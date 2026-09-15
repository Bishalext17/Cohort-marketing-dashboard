from fastapi import APIRouter, Header, HTTPException, Request
from backend.app.core.config import settings
from backend.app.services.cache_manager import cache_manager
from backend.app.core.audit_logger import audit_logger, AuditCategory, AuditLevel
import hmac

router = APIRouter(prefix="/internal", tags=["Internal Service Endpoints"])


def _require_service_token(x_pipeline_token: str) -> None:
    """Machine-to-machine auth for the nightly job (no user JWT available there)."""
    expected = settings.PIPELINE_SERVICE_TOKEN
    if not expected:
        raise HTTPException(status_code=503, detail="PIPELINE_SERVICE_TOKEN is not configured on this server.")
    if not x_pipeline_token or not hmac.compare_digest(x_pipeline_token, expected):
        raise HTTPException(status_code=401, detail="Invalid pipeline service token.")


@router.post("/cache/clear")
def pipeline_clear_cache(request: Request, x_pipeline_token: str = Header(default="")):
    """Flush the web service's in-memory cache after the nightly data refresh."""
    _require_service_token(x_pipeline_token)
    cleared_count = cache_manager.clear()
    audit_logger.log_event(
        category=AuditCategory.CACHE_INVALIDATION,
        action="PIPELINE_CACHE_FLUSH",
        level=AuditLevel.INFO,
        ip_address=request.client.host if request.client else "internal",
        details={"cleared_entries_count": cleared_count}
    )
    return {"success": True, "cleared_count": cleared_count}
