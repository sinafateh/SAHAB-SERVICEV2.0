from app.routes.auth import router as auth_router
from app.routes.reception import router as reception_router
from app.routes.user_panel import router as user_panel_router
from app.routes.workflow import router as workflow_router

__all__ = [
    "auth_router",
    "reception_router",
    "user_panel_router",
    "workflow_router",
]
