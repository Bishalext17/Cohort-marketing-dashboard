import asyncio
from fastapi import APIRouter, BackgroundTasks
from backend.app.services.cache_manager import cache_manager
from backend.app.services.cohort_service import cohort_service

router = APIRouter(prefix="/cache", tags=["Cache Management"])

@router.get("/status")
def get_cache_status():
    """Retrieve cache hit/miss metrics, total cached objects, and background warm-up status."""
    return cache_manager.get_stats()

@router.post("/clear")
def clear_cache():
    """Flushes all stored entries from the in-memory cache."""
    cleared_count = cache_manager.clear()
    return {
        "success": True,
        "message": f"Successfully cleared {cleared_count} cache entries.",
        "cleared_count": cleared_count
    }

@router.post("/prewarm")
async def trigger_prewarm(background_tasks: BackgroundTasks):
    """Triggers an immediate background pre-warming of default cohort windows."""
    background_tasks.add_task(cache_manager.run_prewarm_cycle, cohort_service)
    return {
        "success": True,
        "message": "Background cache pre-warming cycle initiated."
    }
