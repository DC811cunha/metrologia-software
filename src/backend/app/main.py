import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api import analyses, auth, reports, repositories
from app.core.config import settings
from app.core.rate_limit import get_rate_limiter, rule_for

app = FastAPI(title="SoftMeter API", version="0.1.0")

# ── middleware (outermost first via add_middleware call order) ─────────────────

# 1. CORS — must be present for browser preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_MAX_BODY_BYTES = 64 * 1024  # 64 KB
_PAYLOAD_TOO_LARGE_BODY = json.dumps({"detail": "Payload muito grande (máximo 64 KB)"}).encode("utf-8")


class _PayloadTooLarge(Exception):
    pass


class _ContentSizeLimitMiddleware:
    """Rejeita corpos acima de 64 KB (payload flooding). Confere o Content-Length declarado e,
    como `Transfer-Encoding: chunked` não tem esse cabeçalho, também conta os bytes realmente
    recebidos — só olhar o cabeçalho deixaria requisições em chunks passarem sem limite."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > _MAX_BODY_BYTES:
            await self._reject(send)
            return

        received = 0
        response_started = False
        rejected = False

        async def limited_receive() -> Message:
            nonlocal received, rejected
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > _MAX_BODY_BYTES:
                    # O FastAPI engole exceções da leitura do corpo e as converte em 400, então a
                    # resposta 413 é enviada aqui mesmo e o que a aplicação tentar enviar depois
                    # é descartado.
                    if not response_started and not rejected:
                        rejected = True
                        await self._reject(send)
                    raise _PayloadTooLarge
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if rejected:
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _PayloadTooLarge:
            pass

    @staticmethod
    async def _reject(send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(_PAYLOAD_TOO_LARGE_BODY)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": _PAYLOAD_TOO_LARGE_BODY})


# 2. Request body size limit
app.add_middleware(_ContentSizeLimitMiddleware)


class _RateLimitMiddleware(BaseHTTPMiddleware):
    """Limita por IP as rotas sensíveis (ver `app.core.rate_limit.rule_for`): login e recuperação de
    senha sempre; cadastro, refresh e criação de análises em produção."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        rule = rule_for(request.method, request.url.path)
        if rule is not None:
            ip = request.client.host if request.client else "unknown"
            retry_after = await get_rate_limiter().hit(f"{rule.name}:{ip}", rule.limit, rule.window_s)
            if retry_after is not None:
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"Muitas tentativas. Tente novamente em {retry_after} segundos."},
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)


# 3. Rate limiter (outermost — first to see requests)
app.add_middleware(_RateLimitMiddleware)

# ── exception handlers ────────────────────────────────────────────────────────


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


app.include_router(auth.router)
app.include_router(repositories.router)
app.include_router(analyses.router)
app.include_router(reports.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
