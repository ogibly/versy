from fastapi import APIRouter

from app.api.assets import router as assets_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.evaluations import router as evaluations_router
from app.api.ingestion import router as ingestion_router
from app.api.policies import router as policies_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(assets_router)
api_router.include_router(policies_router)
api_router.include_router(evaluations_router)
api_router.include_router(ingestion_router)
