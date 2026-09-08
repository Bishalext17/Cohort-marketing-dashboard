from fastapi import APIRouter
from backend.app.api.v1.kpis import router as kpis_router
from backend.app.api.v1.cohorts import router as cohorts_router
from backend.app.api.v1.metadata import router as metadata_router
from backend.app.api.v1.devices import router as devices_router
from backend.app.api.v1.followups import router as followups_router

api_v1_router = APIRouter()
api_v1_router.include_router(kpis_router)
api_v1_router.include_router(cohorts_router)
api_v1_router.include_router(metadata_router)
api_v1_router.include_router(devices_router)
api_v1_router.include_router(followups_router)
