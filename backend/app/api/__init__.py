from fastapi import APIRouter

from app.api.emails import router as emails_router
from app.api.evaluations import router as evaluations_router
from app.api.health import router as health_router
from app.api.inquiry import router as inquiry_router
from app.api.lookup import router as lookup_router
from app.api.teams import router as teams_router
from app.api.tools import router as tools_router
from app.api.workflows import router as workflows_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(lookup_router, prefix="/api/v1/lookup", tags=["lookup"])
api_router.include_router(tools_router, prefix="/api/v1/tools", tags=["tools"])
api_router.include_router(inquiry_router, prefix="/api/v1/inquiry", tags=["inquiry"])
api_router.include_router(
    workflows_router, prefix="/api/v1/workflows", tags=["workflows"]
)
api_router.include_router(emails_router, prefix="/api/v1/emails", tags=["emails"])
api_router.include_router(teams_router, prefix="/api/v1/teams", tags=["teams"])
api_router.include_router(
    evaluations_router, prefix="/api/v1/evaluations", tags=["evaluations"]
)
