from fastapi import APIRouter, Body
from typing import Dict, Any, Optional
from pydantic import BaseModel
from backend.app.services.operations_service import operations_service

router = APIRouter(tags=["Campaign Operations"])

class OperationsRequest(BaseModel):
    performanceFrom: Optional[str] = None
    performanceTo: Optional[str] = None
    comparisonFrom: Optional[str] = None
    comparisonTo: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    resultEvent: Optional[str] = "complete_registration"

@router.post("/operations")
async def post_campaign_operations(req: OperationsRequest = Body(...)):
    """
    Campaign Meta Diagnosis & Comparison Windows Endpoint.
    Returns 6-stage funnel summary, 5-driver multiplicative breakdown, and trend series.
    """
    return operations_service.diagnose_performance(
        perf_from=req.performanceFrom,
        perf_to=req.performanceTo,
        comp_from=req.comparisonFrom,
        comp_to=req.comparisonTo,
        filters=req.filters,
        result_event=req.resultEvent or "complete_registration"
    )
