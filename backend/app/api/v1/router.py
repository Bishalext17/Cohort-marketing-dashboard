from fastapi import APIRouter, Depends
from backend.app.core.security import get_current_user
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.kpis import router as kpis_router
from backend.app.api.v1.cohorts import router as cohorts_router
from backend.app.api.v1.metadata import router as metadata_router
from backend.app.api.v1.devices import router as devices_router
from backend.app.api.v1.followups import router as followups_router
from backend.app.api.v1.query_runner import router as query_runner_router

api_v1_router = APIRouter()

# Public Auth Endpoints
api_v1_router.include_router(auth_router)

# Protected Analytics & Query Endpoints (Require Valid Bearer Token)
protected_dependency = [Depends(get_current_user)]
api_v1_router.include_router(kpis_router, dependencies=protected_dependency)
api_v1_router.include_router(cohorts_router, dependencies=protected_dependency)
api_v1_router.include_router(metadata_router, dependencies=protected_dependency)
api_v1_router.include_router(devices_router, dependencies=protected_dependency)
api_v1_router.include_router(followups_router, dependencies=protected_dependency)
api_v1_router.include_router(query_runner_router, dependencies=protected_dependency)


