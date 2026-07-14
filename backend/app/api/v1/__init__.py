"""API v1 routes."""

from fastapi import APIRouter

api_router = APIRouter()

# Routes will be added as phases progress:
# from app.api.v1 import experiences, execution, retrieval, evaluation, dashboard
# api_router.include_router(experiences.router, prefix="/experiences", tags=["experiences"])
# api_router.include_router(execution.router, prefix="/execution", tags=["execution"])
# api_router.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
# api_router.include_router(evaluation.router, prefix="/evaluation", tags=["evaluation"])
# api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
