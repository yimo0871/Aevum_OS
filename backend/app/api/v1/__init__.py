"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1.experiences import router as experiences_router
from app.api.v1.execution import router as execution_router
from app.api.v1.retrieval import router as retrieval_router

api_router = APIRouter()

# ── Experience routes ──
api_router.include_router(
    experiences_router, prefix="/experiences", tags=["experiences"]
)

# ── Execution routes ──
api_router.include_router(
    execution_router, prefix="/execution", tags=["execution"]
)

# ── Retrieval routes ──
api_router.include_router(
    retrieval_router, prefix="/retrieval", tags=["retrieval"]
)

# Routes will be added as phases progress:
# api_router.include_router(evaluation.router, prefix="/evaluation", tags=["evaluation"])
# api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
