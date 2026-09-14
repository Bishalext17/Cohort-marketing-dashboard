from fastapi import APIRouter, Query
from typing import Optional
from backend.app.services.company_service import company_service

router = APIRouter(tags=["Company Revenue"])

@router.get("/revenue")
async def get_company_revenue(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    market: Optional[str] = Query(None),
    course: Optional[str] = Query(None),
    slice_by: str = Query("date", alias="slice")
):
    """
    Company Level ROAS & Financial Analytics Endpoint.
    Returns calendar facts, monthly summaries, and market/course segment breakdowns.
    """
    return company_service.calculate_company_view(
        from_date=from_date,
        to_date=to_date,
        market=market,
        course=course,
        slice_by=slice_by
    )
