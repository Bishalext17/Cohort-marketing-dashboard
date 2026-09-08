from fastapi import APIRouter
from backend.app.models.schemas import DeviceComparisonResponse
from backend.app.services.cohort_service import cohort_service

router = APIRouter(prefix="/devices", tags=["Device Diagnostics"])

@router.get("/comparison", response_model=DeviceComparisonResponse)
def get_device_comparison():
    """Retrieve iOS vs Android device funnel comparison highlighting the attendance gap."""
    return cohort_service.get_device_comparison()
