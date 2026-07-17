"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.agents import router as agents_router
from app.api.v1.auth import router as auth_router
from app.api.v1.communities import router as communities_router
from app.api.v1.cocreation import router as cocreation_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.execution import router as execution_router
from app.api.v1.experiences import router as experiences_router
from app.api.v1.federation import router as federation_router
from app.api.v1.governance import router as governance_router
from app.api.v1.human import router as human_router
from app.api.v1.marketplace import router as marketplace_router
from app.api.v1.retrieval import router as retrieval_router

api_router = APIRouter()

# ── Auth routes ──
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# ── Agent management routes ──
api_router.include_router(agents_router, prefix="/agents", tags=["agents"])

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

# ── Evaluation routes ──
api_router.include_router(
    evaluation_router, prefix="/evaluation", tags=["evaluation"]
)

# ── Governance routes ──
api_router.include_router(
    governance_router, prefix="/governance", tags=["governance"]
)

# ── Admin routes ──
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])

# ── Community routes ──
api_router.include_router(
    communities_router, prefix="/communities", tags=["communities"]
)

# ── Human Expression routes (双世界架构 - 人类表达层) ──
api_router.include_router(
    human_router, prefix="/human", tags=["human"]
)

# ── Marketplace routes (经验交易市场) ──
api_router.include_router(
    marketplace_router, prefix="/marketplace", tags=["marketplace"]
)

# ── Federation routes (联邦网络) ──
api_router.include_router(
    federation_router, prefix="/federation", tags=["federation"]
)

# ── Co-creation routes (人机协同创作) ──
api_router.include_router(
    cocreation_router, prefix="/cocreation", tags=["cocreation"]
)
