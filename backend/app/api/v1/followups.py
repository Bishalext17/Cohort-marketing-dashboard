from fastapi import APIRouter, Query, Response, HTTPException, Request
from backend.app.models.schemas import FollowUpListResponse, FollowUpContact, UpdateLeadStatusRequest
from backend.app.services.cohort_service import cohort_service
from backend.app.core.audit_logger import audit_logger, AuditCategory, AuditLevel
import csv
import io

router = APIRouter(prefix="/followups", tags=["Follow-up Contact Lists"])

@router.get("", response_model=FollowUpListResponse)
def get_followup_contacts(category: str = Query("all", description="Category: all, conversions_14d, attended_not_paid, demos_booked_3d")):
    """Retrieve actionable contact lists for sales and admissions follow-up."""
    return cohort_service.get_followup_contacts(category)

@router.patch("/{lead_id}", response_model=FollowUpContact)
def update_lead_status(lead_id: str, req: UpdateLeadStatusRequest, request: Request = None):
    """Update CRM status, follow-up priority, and notes for a specific lead."""
    updated = cohort_service.update_lead_status(
        lead_id=lead_id,
        status=req.status,
        priority=req.followup_priority,
        notes=req.notes
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Lead ID not found.")
    
    client_ip = request.client.host if (request and request.client) else "internal"
    audit_logger.log_event(
        category=AuditCategory.LEAD_MUTATION,
        action="LEAD_STATUS_UPDATE",
        level=AuditLevel.INFO,
        ip_address=client_ip,
        details={
            "lead_id": lead_id,
            "new_status": req.status,
            "new_priority": req.followup_priority,
            "notes": req.notes,
            "parent_name": updated.parent_name
        }
    )
    return updated

@router.get("/export-csv")
def export_followup_csv(category: str = Query("all")):
    """Export filtered follow-up contacts directly to downloadable CSV."""
    res = cohort_service.get_followup_contacts(category)
    output = io.StringIO()
    writer = csv.writer(output)
    
    # CSV Header
    writer.writerow(["Lead ID", "Parent Name", "Phone", "Lead Date", "Course", "Campaign", "OS", "Status", "Attended", "Converted", "Revenue (INR)", "Priority", "Notes"])
    
    for c in res.contacts:
        writer.writerow([
            c.lead_id,
            c.parent_name,
            c.phone,
            c.lead_date,
            c.course,
            c.campaign_name,
            c.os_family,
            c.status,
            "Yes" if c.attended else "No",
            "Yes" if c.converted else "No",
            c.amount,
            c.followup_priority,
            c.notes or ""
        ])
    
    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=followup_{category}.csv"}
    )

