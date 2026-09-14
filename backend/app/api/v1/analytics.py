from fastapi import APIRouter, Body
from typing import Dict, Any, Optional
from pydantic import BaseModel
from backend.app.services.analytics_service import analytics_service

router = APIRouter(tags=["Cohort Analytics"])

class AnalyticsRequest(BaseModel):
    mode: Optional[str] = "cohort"
    period: Optional[str] = "Till date"
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    group: Optional[list] = None
    sort: Optional[str] = "spend"
    direction: Optional[str] = "desc"
    resultEvent: Optional[str] = "complete_registration"
    bookingEvent: Optional[str] = "complete_registration"

@router.post("/analytics")
async def post_cohort_analytics(req: AnalyticsRequest = Body(...)):
    """
    Cohort Performance Explorer & Heatmap Analytics Endpoint.
    Enforces maturity gating, dynamic grouping, and sum-first unit metrics.
    """
    return analytics_service.query_analytics(
        mode=req.mode or "cohort",
        period=req.period or "Till date",
        from_date=req.from_date,
        to_date=req.to_date,
        filters=req.filters,
        group=req.group,
        sort=req.sort or "spend",
        direction=req.direction or "desc",
        result_event=req.resultEvent or "complete_registration",
        booking_event=req.bookingEvent or "complete_registration"
    )
