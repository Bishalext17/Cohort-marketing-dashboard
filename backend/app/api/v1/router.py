from fastapi import APIRouter, Depends
from backend.app.core.security import get_current_user
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.kpis import router as kpis_router
from backend.app.api.v1.cohorts import router as cohorts_router
from backend.app.api.v1.metadata import router as metadata_router
from backend.app.api.v1.devices import router as devices_router
from backend.app.api.v1.followups import router as followups_router
from backend.app.api.v1.cache import router as cache_router
from backend.app.api.v1.internal import router as internal_router
from backend.app.api.v1.audit import router as audit_router

# v14 Production Standard Routers
from backend.app.api.v1.revenue import router as revenue_router
from backend.app.api.v1.analytics import router as analytics_router
from backend.app.api.v1.operations import router as operations_router
from backend.app.api.v1.catalog import router as catalog_router

api_v1_router = APIRouter()

# Public Auth Endpoints
api_v1_router.include_router(auth_router)

# v14 Core Intelligence Endpoints (Direct Access & Integrated UI)
api_v1_router.include_router(catalog_router)
api_v1_router.include_router(revenue_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(operations_router)

# Service-token protected (nightly pipeline -> web service); no user JWT
api_v1_router.include_router(internal_router)

# Protected Analytics & Query Endpoints
protected_dependency = [Depends(get_current_user)]
api_v1_router.include_router(kpis_router, dependencies=protected_dependency)
api_v1_router.include_router(cohorts_router, dependencies=protected_dependency)
api_v1_router.include_router(metadata_router, dependencies=protected_dependency)
api_v1_router.include_router(devices_router, dependencies=protected_dependency)
api_v1_router.include_router(followups_router, dependencies=protected_dependency)
api_v1_router.include_router(cache_router, dependencies=protected_dependency)
api_v1_router.include_router(audit_router, dependencies=protected_dependency)




