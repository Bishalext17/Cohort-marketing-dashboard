import time
import threading
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from collections import OrderedDict
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Thread-Safe Multi-Tier In-Memory LRU Cache with TTL support,
    instrumentation metrics, and background asynchronous pre-warming.
    """

    def __init__(self, max_entries: int = 500):
        self.max_entries = max_entries
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()
        
        # Instrumentation Metrics
        self._hits: int = 0
        self._misses: int = 0
        self._last_prewarmed_at: Optional[float] = None
        self._prewarm_task: Optional[asyncio.Task] = None

    def get(self, key: str) -> Optional[Any]:
        if not settings.CACHE_ENABLED:
            return None

        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]
            now = time.time()
            if now > entry["expires_at"]:
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (MRU)
            self._cache.move_to_end(key)
            self._hits += 1
            return entry["data"]

    def set(self, key: str, data: Any, ttl: Optional[int] = None):
        if not settings.CACHE_ENABLED:
            return

        ttl_seconds = ttl if ttl is not None else settings.CACHE_TTL_SECONDS
        now = time.time()

        with self._lock:
            # Evict LRU if full
            if len(self._cache) >= self.max_entries and key not in self._cache:
                self._cache.popitem(last=False)

            self._cache[key] = {
                "created_at": now,
                "expires_at": now + ttl_seconds,
                "data": data
            }
            self._cache.move_to_end(key)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        with self._lock:
            keys_to_del = [k for k in self._cache.keys() if k.startswith(prefix)]
            for k in keys_to_del:
                del self._cache[k]
            return len(keys_to_del)

    def clear(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_requests = self._hits + self._misses
            hit_ratio = round((self._hits / total_requests * 100), 1) if total_requests > 0 else 0.0
            return {
                "enabled": settings.CACHE_ENABLED,
                "total_entries": len(self._cache),
                "max_entries": self.max_entries,
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio_pct": hit_ratio,
                "default_ttl_seconds": settings.CACHE_TTL_SECONDS,
                "prewarm_enabled": settings.CACHE_PREWARM_ENABLED,
                "last_prewarmed_at": (
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self._last_prewarmed_at))
                    if self._last_prewarmed_at else "Never"
                )
            }

    async def run_prewarm_cycle(self, cohort_service_ref):
        """
        Background worker that pre-warms default cohort views (Till date, D0, D3, D7, D14, D30)
        so incoming user dashboard requests hit 100% memory cache (< 1ms).
        """
        from backend.app.models.schemas import FilterParams
        from backend.app.core.database import check_db_connection

        if not settings.CACHE_PREWARM_ENABLED or not check_db_connection():
            return

        logger.info("Starting background cache pre-warm cycle...")
        cohorts_to_warm = ["Till date", "D0", "D3", "D7", "D14", "D30"]

        for c_period in cohorts_to_warm:
            try:
                filters = FilterParams(cohort_period=c_period, force_refresh=True)
                cohort_service_ref.calculate_cohort_performance(filters)
                cohort_service_ref.calculate_kpis(filters)
                await asyncio.sleep(0.5) # Gentle rate limiter between pre-warm queries
            except Exception as e:
                logger.warning(f"Error pre-warming cohort {c_period}: {e}")

        self._last_prewarmed_at = time.time()
        logger.info("Cache pre-warm cycle completed successfully.")

    def start_background_prewarmer(self, cohort_service_ref, loop: Optional[asyncio.AbstractEventLoop] = None):
        """Spawns recurring background pre-warming loop."""
        if not settings.CACHE_PREWARM_ENABLED:
            return

        async def _prewarm_loop():
            # Initial warm-up after 5 seconds on startup
            await asyncio.sleep(5)
            while True:
                try:
                    await self.run_prewarm_cycle(cohort_service_ref)
                except Exception as e:
                    logger.error(f"Cache prewarmer error: {e}")
                
                interval_secs = max(60, settings.CACHE_PREWARM_INTERVAL_MINUTES * 60)
                await asyncio.sleep(interval_secs)

        try:
            if loop is None:
                loop = asyncio.get_event_loop()
            if loop.is_running():
                self._prewarm_task = loop.create_task(_prewarm_loop())
        except Exception as e:
            logger.debug(f"Could not attach async pre-warmer loop: {e}")

# Global Cache Instance
cache_manager = CacheManager()
