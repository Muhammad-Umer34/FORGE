# D:\FYP\FORGE-1\backend\routes\health.py
from fastapi import APIRouter
from backend.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "model": settings.CLARIFICATION_MODEL
    }
