from fastapi import APIRouter

from app.api.incidents import router as incidents_router
from app.api.reliability import router as reliability_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(incidents_router)
api_router.include_router(reliability_router)
