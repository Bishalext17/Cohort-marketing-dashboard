#!/usr/bin/env python3
"""
run_daily_pipeline.py
=============================================================================
Unified Master Daily Pipeline Orchestrator.

Execution Chain:
1. Ingest Meta Marketing Ads Data (ingest_meta_direct.py)
2. Synchronize Materialized Cohort Cache (sync_cohort_cache.py)
3. Execute Checksum Reconciliation & Quality Controls (verify_reconciliation.py)
4. Flush Backend In-Memory & Redis Query Caches
=============================================================================
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime, timedelta

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)
for p in [ROOT_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.scripts.ingest_meta_direct import MetaDirectIngestionEngine
from backend.scripts.sync_cohort_cache import CohortCacheSyncEngine
from backend.scripts.verify_reconciliation import ReconciliationEngine
from backend.app.core.config import settings
from backend.app.core.audit_logger import audit_logger, AuditCategory, AuditLevel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [master_pipeline] %(message)s"
)
logger = logging.getLogger("run_daily_pipeline")


def flush_backend_cache(dry_run: bool = False) -> bool:
    """
    Ask the running web service to drop its in-memory query cache. The job runs
    in its own container, so clearing a local cache object here would do
    nothing for the dashboard. Failures are logged, never fatal: the data is
    already in the database and the web cache expires on its own TTL.
    """
    base_url = (settings.BACKEND_BASE_URL or "").rstrip("/")
    if not base_url:
        logger.warning("BACKEND_BASE_URL not set; skipping web cache flush (entries expire by TTL).")
        return False
    if not settings.PIPELINE_SERVICE_TOKEN:
        logger.warning("PIPELINE_SERVICE_TOKEN not set; skipping web cache flush.")
        return False
    if dry_run:
        logger.info(f"[DRY-RUN] Would POST {base_url}{settings.API_V1_STR}/internal/cache/clear")
        return True

    import requests
    url = f"{base_url}{settings.API_V1_STR}/internal/cache/clear"
    try:
        resp = requests.post(url, headers={"X-Pipeline-Token": settings.PIPELINE_SERVICE_TOKEN}, timeout=20)
        if resp.ok:
            cleared = resp.json().get("cleared_count", "?")
            logger.info(f"Flushed {cleared} cached entries on {base_url}. REST endpoints will serve fresh data.")
            return True
        logger.warning(f"Web cache flush returned HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Web cache flush failed: {e}")
    return False


def run_master_pipeline(
    days: int = 7,
    date_from: str = None,
    date_to: str = None,
    mode: str = "incremental",
    dry_run: bool = False
) -> bool:
    """Executes the complete end-to-end data pipeline with failure safeguards."""
    start_total = time.time()
    now = datetime.now()

    if not date_from or not date_to:
        date_from = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        date_to = now.strftime("%Y-%m-%d")

    logger.info("=" * 70)
    logger.info(f"🚀 STARTING MASTER DAILY MARKETING PIPELINE")
    logger.info(f"Target Window: {date_from} to {date_to} | Mode: {mode} | Dry-Run: {dry_run}")
    logger.info("=" * 70)

    # ── STAGE 1: META ADS INGESTION ──────────────────────────────────────────
    logger.info("\n▶ STAGE 1/4: Ingesting Meta Ads Delivery Feed...")
    ingest_engine = MetaDirectIngestionEngine(dry_run=dry_run)
    ingest_res = ingest_engine.run_sync(date_from=date_from, date_to=date_to)
    if ingest_res["status"] != "SUCCESS":
        logger.error(f"❌ Stage 1 Failed: {ingest_res.get('error')}")
        return False

    # ── STAGE 2: COHORT CACHE SYNCHRONIZATION ────────────────────────────────
    logger.info("\n▶ STAGE 2/4: Synchronizing Materialized Cohort Cache...")
    cache_engine = CohortCacheSyncEngine(dry_run=dry_run)
    cache_res = cache_engine.run_sync(mode=mode, custom_from=date_from, custom_to=date_to)
    if cache_res["status"] != "SUCCESS":
        logger.error(f"❌ Stage 2 Failed: {cache_res.get('error')}")
        return False

    # ── STAGE 3: RECONCILIATION & QUALITY CONTROLS ───────────────────────────
    logger.info("\n▶ STAGE 3/4: Running Quality Control & Reconciliation Suite...")
    reconcile_engine = ReconciliationEngine(dry_run=dry_run)
    reconcile_res = reconcile_engine.run_all_checks(date_from=date_from, date_to=date_to)
    if reconcile_res["status"] != "PASSED":
        if settings.RECONCILIATION_STRICT:
            logger.error("❌ Stage 3 Failed: Discrepancy detected in reconciliation (RECONCILIATION_STRICT=true).")
            return False
        # Reconciliation is a quality report; a mismatch must not stop the
        # dashboard from being refreshed with the data that did load.
        logger.warning("⚠️ Stage 3: reconciliation reported discrepancies; continuing (RECONCILIATION_STRICT=false).")

    # ── STAGE 4: CACHE INVALIDATION ──────────────────────────────────────────
    logger.info("\n▶ STAGE 4/4: Flushing Backend Query Cache...")
    flush_backend_cache(dry_run=dry_run)

    total_sec = round(time.time() - start_total, 2)
    logger.info("\n" + "=" * 70)
    logger.info(f"✅ MASTER DAILY MARKETING PIPELINE COMPLETED IN {total_sec}s")
    logger.info("=" * 70)

    audit_logger.log_event(
        category=AuditCategory.QUERY_EXECUTION,
        action="MASTER_PIPELINE_COMPLETE",
        level=AuditLevel.INFO,
        duration_ms=total_sec * 1000,
        details={
            "date_from": date_from,
            "date_to": date_to,
            "mode": mode,
            "dry_run": dry_run,
            "duration_sec": total_sec
        }
    )

    return True


def main():
    parser = argparse.ArgumentParser(description="Master Daily Marketing Pipeline Orchestrator")
    parser.add_argument("--days", type=int, default=7, help="Number of past days to sync (default: 7 for rolling conversion capture)")
    parser.add_argument("--date-from", type=str, help="Custom start date (YYYY-MM-DD)")
    parser.add_argument("--date-to", type=str, help="Custom end date (YYYY-MM-DD)")
    parser.add_argument("--mode", choices=["incremental", "full"], default="incremental", help="Cache sync mode")
    parser.add_argument("--dry-run", action="store_true", help="Run without database writes")

    args = parser.parse_args()

    success = run_master_pipeline(
        days=args.days,
        date_from=args.date_from,
        date_to=args.date_to,
        mode=args.mode,
        dry_run=args.dry_run
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
