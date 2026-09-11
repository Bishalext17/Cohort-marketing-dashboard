from fastapi import APIRouter, Query, Request
from typing import Optional, List, Dict, Any
from backend.app.core.audit_logger import audit_logger, AuditCategory, AuditLevel

router = APIRouter(prefix="/audit", tags=["Audit & Critical Change Logs"])

@router.get("/logs")
def get_audit_logs(
    category: Optional[str] = Query(None, description="Filter by category: QUERY_EXECUTION, LEAD_MUTATION, CACHE_INVALIDATION, AUTH_EVENT, SYSTEM_ERROR"),
    level: Optional[str] = Query(None, description="Filter by level: INFO, WARNING, ERROR"),
    search: Optional[str] = Query(None, description="Search keyword in event details or parameters"),
    limit: int = Query(50, ge=1, le=200, description="Max number of logs to return"),
    offset: int = Query(0, ge=0, description="Pagination offset")
) -> Dict[str, Any]:
    """
    Retrieve structured audit logs from the in-memory ring-buffer.
    Safe against memory leaks (bounded buffer).
    """
    logs = audit_logger.get_logs(
        category=category,
        level=level,
        search=search,
        limit=limit,
        offset=offset
    )
    return {
        "success": True,
        "count": len(logs),
        "limit": limit,
        "offset": offset,
        "logs": logs
    }

@router.get("/stats")
def get_audit_stats() -> Dict[str, Any]:
    """
    Retrieve memory consumption, disk size, and health stats of the audit logging system.
    """
    stats = audit_logger.get_stats()
    return {
        "success": True,
        "stats": stats
    }

@router.post("/flush")
def flush_audit_memory(request: Request = None) -> Dict[str, Any]:
    """
    Flushes the in-memory ring-buffer and synchronizes disk log files immediately.
    Ensures zero lingering memory usage.
    """
    cleared_count = audit_logger.flush_memory()
    client_ip = request.client.host if (request and request.client) else "internal"
    audit_logger.log_event(
        category=AuditCategory.CACHE_INVALIDATION,
        action="AUDIT_MEMORY_FLUSHED",
        level=AuditLevel.INFO,
        ip_address=client_ip,
        details={"cleared_in_memory_events": cleared_count}
    )
    return {
        "success": True,
        "message": f"Successfully flushed {cleared_count} events from RAM buffer to disk.",
        "flushed_count": cleared_count
    }
