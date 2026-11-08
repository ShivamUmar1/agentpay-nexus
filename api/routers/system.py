from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from api.config import settings
from api.services.llm_provider import llm_provider

router = APIRouter(prefix="/api", tags=["System"])


@router.get("/health")
def health_check():
    """Liveness probe."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/system/status")
def system_status():
    """Minimal public service health status without active database queries, external network calls, or credential leaks."""
    env_label = "production" if settings.is_production else settings.APP_ENV
    return {
        "status": "operational",
        "service": settings.APP_NAME,
        "environment": env_label,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/system/test-ai")
@router.post("/system/test-ai")
async def test_ai_connection():
    """Bounded live diagnostic endpoint for testing active AI inference.
    Disabled in production by default. Only accessible in explicitly non-production environments
    when explicitly enabled via ENABLE_LIVE_AI_DIAGNOSTICS configuration.
    """
    if settings.is_production or not settings.ENABLE_LIVE_AI_DIAGNOSTICS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Live AI diagnostics are disabled in this environment."
        )
    return await llm_provider.test_connection()
