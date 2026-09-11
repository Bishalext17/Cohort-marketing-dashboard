import asyncio
from fastapi import APIRouter, BackgroundTasks, Request
from backend.app.services.cache_manager import cache_manager
from backend.app.services.cohort_service import cohort_service
from backend.app.core.audit_logger import audit_logger, AuditCategory, AuditLevel

router = APIRouter(prefix="/cache", tags=["Cache Management"])

@router.get("/status")
def get_cache_status():
    """Retrieve cache hit/miss metrics, total cached objects, and background warm-up status."""
    return cache_manager.get_stats()

@router.post("/clear")
def clear_cache(request: Request = None):
    """Flushes all stored entries from the in-memory cache."""
    cleared_count = cache_manager.clear()
    client_ip = request.client.host if (request and request.client) else "internal"
    audit_logger.log_event(
        category=AuditCategory.CACHE_INVALIDATION,
        action="MANUAL_CACHE_FLUSH",
        level=AuditLevel.INFO,
        ip_address=client_ip,
        details={"cleared_entries_count": cleared_count}
    )
    return {
        "success": True,
        "message": f"Successfully cleared {cleared_count} cache entries.",
        "cleared_count": cleared_count
    }

@router.post("/prewarm")
async def trigger_prewarm(background_tasks: BackgroundTasks, request: Request = None):
    """Triggers an immediate background pre-warming of default cohort windows."""
    background_tasks.add_task(cache_manager.run_prewarm_cycle, cohort_service)
    client_ip = request.client.host if (request and request.client) else "internal"
    audit_logger.log_event(
        category=AuditCategory.CACHE_INVALIDATION,
        action="PREWARM_INITIATED",
        level=AuditLevel.INFO,
        ip_address=client_ip,
        details={"status": "background_task_scheduled"}
    )
    return {
        "success": True,
        "message": "Background cache pre-warming cycle initiated."
    }
