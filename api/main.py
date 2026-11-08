from urllib.parse import urlparse
from typing import Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from api.config import settings
from api.database import init_db
from api.routers import (
    agents_router,
    tasks_router,
    workflow_router,
    payments_router,
    system_router
)


def is_trusted_origin(origin_header: Optional[str], allowed_origins: List[str]) -> bool:
    """Verifies that an Origin header matches one of the explicitly trusted frontend origins."""
    if not origin_header or not origin_header.strip():
        return False
    clean = origin_header.strip().rstrip("/")
    if clean == "null" or clean.startswith("javascript:"):
        return False
    try:
        parsed = urlparse(clean)
        if not parsed.scheme or not parsed.netloc:
            return False
        normalized = f"{parsed.scheme}://{parsed.netloc}".lower()
        allowed_normalized = []
        for o in allowed_origins:
            if o == "*":
                continue
            p = urlparse(o.strip().rstrip("/"))
            if p.scheme and p.netloc:
                allowed_normalized.append(f"{p.scheme}://{p.netloc}".lower())
        return normalized in allowed_normalized
    except Exception:
        return False


def extract_origin_from_referer(referer_header: Optional[str]) -> Optional[str]:
    """Extracts scheme://host origin from a Referer header."""
    if not referer_header or not referer_header.strip():
        return None
    try:
        p = urlparse(referer_header.strip())
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}".lower()
    except Exception:
        pass
    return None


class SecurityAndBodyLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Quick Content-Length header guard
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"Payload Too Large: Maximum allowed request body size is {settings.MAX_REQUEST_BODY_BYTES // 1024} KB."}
                    )
            except ValueError:
                pass

        # 2. CSRF Origin / Referer validation on state-changing requests
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            sec_fetch_site = request.headers.get("sec-fetch-site")

            allowed = list(settings.cors_origin_list)
            if settings.APP_BASE_URL:
                allowed.append(settings.APP_BASE_URL)

            # If origin is provided, it MUST be an explicitly trusted origin
            if origin is not None and origin.strip():
                if not is_trusted_origin(origin, allowed):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Cross-origin request forbidden."}
                    )
            # If origin is absent, but referer is present, verify referer origin
            elif referer is not None and referer.strip():
                ref_orig = extract_origin_from_referer(referer)
                if not ref_orig or not is_trusted_origin(ref_orig, allowed):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Cross-origin referer forbidden."}
                    )
            # If sec-fetch-site indicates browser cross-site request
            elif sec_fetch_site and sec_fetch_site.lower() == "cross-site":
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Cross-site request forbidden."}
                )

        # 3. Stream body validation in case Content-Length was omitted or spoofed
        if request.method in ("POST", "PUT", "PATCH"):
            body = await request.body()
            if len(body) > settings.MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Payload Too Large: Maximum allowed request body size is {settings.MAX_REQUEST_BODY_BYTES // 1024} KB."}
                )

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seeds on startup
    init_db()
    yield


# Guarantee DB initialization on module import
init_db()

app = FastAPI(
    title=settings.APP_NAME,
    description="Autonomous AI Agent Marketplace & PayPal Settlement Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add security & body limit middleware
app.add_middleware(SecurityAndBodyLimitMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(system_router)
app.include_router(agents_router)
app.include_router(tasks_router)
app.include_router(workflow_router)
app.include_router(payments_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to AgentPay Nexus API",
        "docs": "/docs",
        "health": "/api/health",
        "system": "/api/system/status"
    }
