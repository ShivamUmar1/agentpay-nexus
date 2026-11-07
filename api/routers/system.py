import asyncio
from datetime import datetime
from fastapi import APIRouter
from api.config import settings
from api.database import test_db_connection
from api.services.paypal_service import paypal_service
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
async def system_status():
    """Diagnostic endpoint reporting backend integration configurations without triggering external AI calls or timing out."""
    db_status = test_db_connection()
    ai_status = llm_provider.get_status()
    payment_status = await paypal_service.test_connection()

    return {
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "ai_orchestration": ai_status,
        "payment_gateway": payment_status
    }


@router.get("/system/test-ai")
@router.post("/system/test-ai")
async def test_ai_connection():
    """Bounded live diagnostic endpoint for testing active AI inference (max 3.0s timeout)."""
    return await llm_provider.test_connection()
