# D:\FYP\FORGE-1\backend\routes\__init__.py
from backend.routes.chat import router as chat_router
from backend.routes.health import router as health_router
from backend.routes.projects import router as projects_router  # registered once sign-in exists
from backend.routes.requests import router as requests_router

__all__ = ["chat_router", "health_router", "projects_router", "requests_router"]
