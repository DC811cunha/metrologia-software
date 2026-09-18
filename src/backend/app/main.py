import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import analyses, auth, reports, repositories
from app.core.config import settings

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


class _ContentSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects requests whose Content-Length exceeds 64 KB (payload flooding)."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > _MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Payload muito grande (máximo 64 KB)"},
            )
        return await call_next(request)


# 2. Request body size limit
app.add_middleware(_ContentSizeLimitMiddleware)

# Chave é "path:ip" — cada endpoint sensível tem sua própria janela, então
# esgotar o limite de login não afeta o de forgot-password e vice-versa.
_login_window: dict[str, deque[float]] = defaultdict(deque)
_RATE_WINDOW_S = 60
_RATE_MAX = 10  # tentativas por minuto por IP
_RATE_LIMITED_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
}


class _LoginRateLimitMiddleware(BaseHTTPMiddleware):
    """Limita tentativas de login e de recuperação de senha a 10/minuto por IP —
    forgot-password mitiga brute-force e spam de e-mail/enumeração de contas;
    reset-password entra pelo mesmo motivo por defesa em profundidade (o token
    já tem 256 bits de entropia, mas o endpoint não tinha nenhum limite antes)."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.url.path in _RATE_LIMITED_PATHS and request.method == "POST":
            ip = (request.client.host if request.client else "unknown")
            key = f"{request.url.path}:{ip}"
            now = time.monotonic()
            window = _login_window[key]
            while window and window[0] < now - _RATE_WINDOW_S:
                window.popleft()
            if len(window) >= _RATE_MAX:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Muitas tentativas. Tente novamente em um minuto."},
                    headers={"Retry-After": "60"},
                )
            window.append(now)
        return await call_next(request)


# 3. Login rate limiter (outermost — first to see requests)
app.add_middleware(_LoginRateLimitMiddleware)

# ── exception handlers ────────────────────────────────────────────────────────


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(auth.router)
app.include_router(repositories.router)
app.include_router(analyses.router)
app.include_router(reports.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
