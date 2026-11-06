from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.database import get_db
from api.config import settings
from api.services.paypal_service import paypal_service
from api.services.llm_provider import llm_provider

router = APIRouter(prefix="/api", tags=["System"])


@router.get("/health")
def health_check():
    """Liveness probe."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0"
    }


@router.get("/system/status")
def system_status(db: Session = Depends(get_db)):
    """Diagnostic endpoint reporting backend integrations without exposing secret keys."""
    # Test DB
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": {
            "status": "connected" if db_ok else "error",
            "type": "postgresql" if "postgres" in settings.DATABASE_URL else "sqlite"
        },
        "ai_orchestration": {
            "provider": llm_provider.provider_name,
            "status": "active",
            "model": settings.GEMINI_MODEL if llm_provider.provider_name == "gemini" else (settings.OPENAI_MODEL if llm_provider.provider_name == "openai" else "deterministic_engine_v1")
        },
        "payment_gateway": {
            "provider": "PayPal REST API v2",
            "mode": settings.PAYPAL_MODE,
            "configured": paypal_service.is_configured,
            "status": "sandbox_ready" if paypal_service.is_configured else "simulated_demo_mode",
            "client_id_set": bool(settings.PAYPAL_CLIENT_ID)
        },
        "version": "1.0.0"
    }
