"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1.experiences import router as experiences_router

api_router = APIRouter()

# ── Experience routes ──
api_router.include_router(
    experiences_router, prefix="/experiences", tags=["experiences"]
)

# Routes will be added as phases progress:
# api_router.include_router(execution.router, prefix="/execution", tags=["execution"])
# api_router.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
# api_router.include_router(evaluation.router, prefix="/evaluation", tags=["evaluation"])
# api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
