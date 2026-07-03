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

_login_window: dict[str, deque[float]] = defaultdict(deque)
_RATE_WINDOW_S = 60
_RATE_MAX = 10  # login attempts per minute per IP


class _LoginRateLimitMiddleware(BaseHTTPMiddleware):
    """Limits login attempts to 10 per minute per IP to prevent brute-force."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.url.path == "/api/v1/auth/login" and request.method == "POST":
            ip = (request.client.host if request.client else "unknown")
            now = time.monotonic()
            window = _login_window[ip]
            while window and window[0] < now - _RATE_WINDOW_S:
                window.popleft()
            if len(window) >= _RATE_MAX:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Muitas tentativas de login. Tente novamente em um minuto."},
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
