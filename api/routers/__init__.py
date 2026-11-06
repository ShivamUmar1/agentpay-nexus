from api.routers.agents import router as agents_router
from api.routers.tasks import router as tasks_router
from api.routers.workflow import router as workflow_router
from api.routers.payments import router as payments_router
from api.routers.system import router as system_router

__all__ = [
    "agents_router",
    "tasks_router",
    "workflow_router",
    "payments_router",
    "system_router"
]
