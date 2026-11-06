from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.config import settings
from api.database import init_db
from api.routers import (
    agents_router,
    tasks_router,
    workflow_router,
    payments_router,
    system_router
)


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
