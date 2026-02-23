"""Health check router."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "metalcore-index-api", "version": "0.1.0"}


@router.get("/")
def root():
    return {
        "service": "Metalcore Index API",
        "version": "0.1.0",
        "docs": "/docs",
    }
