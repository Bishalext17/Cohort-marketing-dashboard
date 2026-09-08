from fastapi import APIRouter
from backend.app.models.schemas import FilterParams, KPITilesResponse
from backend.app.services.cohort_service import cohort_service

router = APIRouter(prefix="/kpis", tags=["KPIs"])

@router.post("", response_model=KPITilesResponse)
def get_kpi_tiles(filters: FilterParams):
    """Retrieve 8-10 unified KPI tiles matching the master TOTAL row exactly."""
    return cohort_service.get_kpis(filters)
