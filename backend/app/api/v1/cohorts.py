from fastapi import APIRouter
from backend.app.models.schemas import FilterParams, CohortMasterResponse, CohortMaturityResponse
from backend.app.services.cohort_service import cohort_service

router = APIRouter(prefix="/cohorts", tags=["Cohorts"])

@router.post("/master", response_model=CohortMasterResponse)
def get_master_cohort_table(filters: FilterParams):
    """Retrieve full master cohort table with multi-dimensional slicing and recalculated totals."""
    return cohort_service.calculate_cohort_performance(filters)

@router.post("/maturity", response_model=CohortMaturityResponse)
def get_cohort_maturity(filters: FilterParams):
    """Retrieve maturity timeline, counted/dropped days, and cohort gate notes."""
    return cohort_service.get_maturity_data(filters.cohort_period, filters)
