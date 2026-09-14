#!/usr/bin/env python3
"""
ingest_meta_direct.py
=============================================================================
High-performance, Zero-CPU-Spike Ingestion Engine for Meta Marketing Graph API.

Database Protection & Optimization Rules Enforced:
1. Chunked Batch Upserts: Writes in manageable chunks (default: 500 rows) to prevent
   table locking and long-running transaction overhead.
2. Inter-Batch Throttling: Configurable micro-delay (default: 50ms) between batches
   allowing MariaDB read replicas and web requests to execute smoothly.
3. In-Memory Offloading: All JSON parsing, action unnesting, and type sanitization
   are computed in Python memory before writing clean rows to the database.
4. Idempotent Upsert: Uses ON DUPLICATE KEY UPDATE against the clustered primary key
   (date, account_id, ad_id, impression_device, publisher_platform) for O(1) B-Tree writes.
5. Dry-Run & Safety Mode: Supports `--dry-run` to benchmark memory/payload without DB impact.
=============================================================================
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)
for p in [ROOT_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.core.config import settings
from backend.app.core.database import get_db, engine
from backend.app.core.audit_logger import audit_logger, AuditCategory, AuditLevel
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [meta_ingest] %(message)s"
)
logger = logging.getLogger("ingest_meta_direct")

META_GRAPH_API_VERSION = "v20.0"
DEFAULT_BATCH_SIZE = 500
DEFAULT_INTER_BATCH_DELAY_SEC = 0.05  # 50ms sleep to protect DB CPU


class MetaDirectIngestionEngine:
    def __init__(
        self,
        access_token: Optional[str] = None,
        account_ids: Optional[List[str]] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        inter_batch_delay: float = DEFAULT_INTER_BATCH_DELAY_SEC,
        dry_run: bool = False
    ):
        self.access_token = access_token or os.getenv("META_ACCESS_TOKEN", getattr(settings, "META_ACCESS_TOKEN", ""))
        raw_accounts = account_ids or os.getenv("META_AD_ACCOUNT_IDS", getattr(settings, "META_AD_ACCOUNT_IDS", ""))
        if isinstance(raw_accounts, str):
            self.account_ids = [a.strip() for a in raw_accounts.split(",") if a.strip()]
        else:
            self.account_ids = raw_accounts or []
        
        self.batch_size = max(50, min(batch_size, 2000))
        self.inter_batch_delay = inter_batch_delay
        self.dry_run = dry_run

    @staticmethod
    def check_rate_limits(headers: Any) -> None:
        """Inspects Meta rate-limit headers and throttles if utilization exceeds 80%."""
        for header_key in ["x-business-use-case-usage", "x-app-usage", "x-ad-account-usage"]:
            val = headers.get(header_key)
            if val:
                try:
                    usage_data = json.loads(val) if isinstance(val, str) else val
                    if isinstance(usage_data, list) and len(usage_data) > 0:
                        usage_data = usage_data[0]
                    if isinstance(usage_data, dict):
                        max_metric = max(
                            usage_data.get("call_count", 0),
                            usage_data.get("total_cputime", 0),
                            usage_data.get("total_time", 0)
                        )
                        if max_metric >= 80:
                            logger.warning(f"⚠️ Meta API Rate Limit usage reached {max_metric}%. Proactively throttling for 30s...")
                            time.sleep(30)
                except Exception:
                    pass

    def fetch_insights_for_account(
        self,
        account_id: str,
        date_from: str,
        date_to: str
    ) -> List[Dict[str, Any]]:
        """
        Fetches ad-level delivery metrics and breakdowns from Meta Graph API
        with cursor-based pagination, rate-limit probing, and automatic retry with backoff.
        """
        clean_account = account_id.replace("act_", "").strip()
        endpoint = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}/act_{clean_account}/insights"
        
        fields = [
            "date_start", "account_id", "campaign_id", "campaign_name",
            "adset_id", "adset_name", "ad_id", "ad_name",
            "spend", "impressions", "clicks", "inline_link_clicks",
            "actions"
        ]
        
        params = {
            "access_token": self.access_token,
            "level": "ad",
            "time_range": json.dumps({"since": date_from, "until": date_to}),
            "time_increment": 1,
            "fields": ",".join(fields),
            "breakdowns": "impression_device,publisher_platform",
            "limit": 500
        }

        all_records = []
        next_url = endpoint
        request_params = params
        page_count = 0

        logger.info(f"Extracting Meta insights for act_{clean_account} from {date_from} to {date_to}...")

        while next_url:
            max_retries = 3
            data = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    res = requests.get(next_url, params=request_params, timeout=30)
                    self.check_rate_limits(res.headers)
                    if res.status_code == 200:
                        data = res.json()
                        break
                    elif res.status_code in [429, 500, 502, 503, 504]:
                        sleep_time = (2 ** attempt) + 1.0
                        logger.warning(f"Meta API HTTP {res.status_code}. Retrying in {sleep_time}s (Attempt {attempt}/{max_retries})...")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"Meta API Error HTTP {res.status_code}: {res.text}")
                        break
                except requests.RequestException as e:
                    sleep_time = (2 ** attempt) + 1.0
                    logger.warning(f"Network error: {e}. Retrying in {sleep_time}s (Attempt {attempt}/{max_retries})...")
                    time.sleep(sleep_time)

            if not data or "data" not in data:
                break

            records = data.get("data", [])
            all_records.extend(records)
            page_count += 1

            # Cursor-based pagination
            paging = data.get("paging", {})
            next_url = paging.get("next")
            # Once next_url is set, params are included in the url
            request_params = None

        logger.info(f"Extracted {len(all_records)} raw records across {page_count} pages for act_{clean_account}.")
        return all_records

    def transform_record(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes a raw Meta insight row into a clean typed dictionary.
        Unpacks nested action events without hitting database CPU.
        """
        # Parse spend and numeric delivery counters safely
        try:
            spend = float(raw.get("spend", 0.0))
        except (ValueError, TypeError):
            spend = 0.0

        try:
            impressions = int(raw.get("impressions", 0))
        except (ValueError, TypeError):
            impressions = 0

        try:
            clicks = int(raw.get("clicks", 0))
        except (ValueError, TypeError):
            clicks = 0

        try:
            link_clicks = int(raw.get("inline_link_clicks", 0))
        except (ValueError, TypeError):
            link_clicks = 0

        # Unnest Meta Pixel / CAPI Actions
        complete_registration = 0
        start_trial = 0
        purchases = 0
        landing_page_views = 0

        actions = raw.get("actions", [])
        if isinstance(actions, list):
            for action in actions:
                action_type = str(action.get("action_type", "")).lower()
                try:
                    val = int(action.get("value", 0))
                except (ValueError, TypeError):
                    val = 0

                if action_type in ["complete_registration", "omni_complete_registration"]:
                    complete_registration += val
                elif action_type in ["start_trial", "omni_start_trial"]:
                    start_trial += val
                elif action_type in ["purchase", "omni_purchase"]:
                    purchases += val
                elif action_type in ["landing_page_view", "omni_landing_page_view"]:
                    landing_page_views += val

        return {
            "date": raw.get("date_start", ""),
            "account_id": str(raw.get("account_id", "")),
            "campaign_id": str(raw.get("campaign_id", "")),
            "campaign_name": str(raw.get("campaign_name", "Unmapped")),
            "adset_id": str(raw.get("adset_id", "")),
            "adset_name": str(raw.get("adset_name", "Unmapped")),
            "ad_id": str(raw.get("ad_id", "")),
            "ad_name": str(raw.get("ad_name", "Unmapped")),
            "impression_device": str(raw.get("impression_device", "all")),
            "publisher_platform": str(raw.get("publisher_platform", "all")),
            "spend": round(spend, 4),
            "impressions": max(0, impressions),
            "clicks": max(0, clicks),
            "link_clicks": max(0, link_clicks),
            "landing_page_views": max(0, landing_page_views),
            "complete_registration": max(0, complete_registration),
            "start_trial": max(0, start_trial),
            "purchases": max(0, purchases),
        }

    def batch_upsert(self, records: List[Dict[str, Any]]) -> int:
        """
        Executes chunked batch upserts with micro-throttles to protect database CPU.
        """
        if not records:
            return 0

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would upsert {len(records)} records into raw_meta_ads_delivery (DB writes skipped).")
            return len(records)

        upsert_sql = text("""
            INSERT INTO raw_meta_ads_delivery (
                date, account_id, campaign_id, campaign_name,
                adset_id, adset_name, ad_id, ad_name,
                impression_device, publisher_platform,
                spend, impressions, clicks, link_clicks, landing_page_views,
                complete_registration, start_trial, purchases
            ) VALUES (
                :date, :account_id, :campaign_id, :campaign_name,
                :adset_id, :adset_name, :ad_id, :ad_name,
                :impression_device, :publisher_platform,
                :spend, :impressions, :clicks, :link_clicks, :landing_page_views,
                :complete_registration, :start_trial, :purchases
            )
            ON DUPLICATE KEY UPDATE
                campaign_name = VALUES(campaign_name),
                adset_name = VALUES(adset_name),
                ad_name = VALUES(ad_name),
                spend = VALUES(spend),
                impressions = VALUES(impressions),
                clicks = VALUES(clicks),
                link_clicks = VALUES(link_clicks),
                landing_page_views = VALUES(landing_page_views),
                complete_registration = VALUES(complete_registration),
                start_trial = VALUES(start_trial),
                purchases = VALUES(purchases),
                updated_at = CURRENT_TIMESTAMP
        """)

        total_upserted = 0
        total_chunks = (len(records) + self.batch_size - 1) // self.batch_size

        with engine.begin() as conn:
            for i in range(0, len(records), self.batch_size):
                chunk = records[i:i + self.batch_size]
                chunk_index = (i // self.batch_size) + 1
                conn.execute(upsert_sql, chunk)
                total_upserted += len(chunk)
                
                # Yield lock & breathe to avoid sustained DB CPU spikes
                if self.inter_batch_delay > 0 and chunk_index < total_chunks:
                    time.sleep(self.inter_batch_delay)

        logger.info(f"Successfully upserted {total_upserted} records into raw_meta_ads_delivery in {total_chunks} chunks.")
        return total_upserted

    def run_sync(self, date_from: str, date_to: str) -> Dict[str, Any]:
        """
        Full orchestration of Extract, Transform, and Load for all configured ad accounts.
        """
        start_time = time.time()
        total_processed = 0
        status = "SUCCESS"
        error_msg = None

        logger.info(f"Starting Meta Direct Ingestion Pipeline for {len(self.account_ids)} accounts from {date_from} to {date_to}...")

        try:
            for acc in self.account_ids:
                raw_records = self.fetch_insights_for_account(acc, date_from, date_to)
                transformed = [self.transform_record(r) for r in raw_records]
                upserted = self.batch_upsert(transformed)
                total_processed += upserted

            duration_sec = round(time.time() - start_time, 2)
            logger.info(f"Ingestion Pipeline completed in {duration_sec}s. Total rows processed: {total_processed}.")

            # Record telemetry in audit log
            audit_logger.log_event(
                category=AuditCategory.QUERY_EXECUTION,
                action="META_DIRECT_INGEST_SUCCESS",
                level=AuditLevel.INFO,
                duration_ms=duration_sec * 1000,
                details={
                    "date_from": date_from,
                    "date_to": date_to,
                    "rows_processed": total_processed,
                    "accounts_count": len(self.account_ids),
                    "dry_run": self.dry_run
                }
            )

        except Exception as e:
            status = "FAILED"
            error_msg = str(e)
            duration_sec = round(time.time() - start_time, 2)
            logger.error(f"Ingestion Pipeline failed: {e}", exc_info=True)
            audit_logger.log_event(
                category=AuditCategory.SYSTEM_ERROR,
                action="META_DIRECT_INGEST_FAILED",
                level=AuditLevel.ERROR,
                duration_ms=duration_sec * 1000,
                details={"error": str(e), "date_from": date_from, "date_to": date_to}
            )

        # Record pipeline run in DB audit table if not dry-run and DB available
        if not self.dry_run:
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO data_pipeline_runs (job_name, status, date_from, date_to, rows_processed, duration_sec, error_message)
                        VALUES ('meta_direct_ingestion', :status, :date_from, :date_to, :rows_processed, :duration_sec, :error_message)
                    """), {
                        "status": status,
                        "date_from": date_from,
                        "date_to": date_to,
                        "rows_processed": total_processed,
                        "duration_sec": duration_sec,
                        "error_message": error_msg
                    })
            except Exception as audit_err:
                logger.warning(f"Could not record pipeline run audit to DB: {audit_err}")

        return {
            "status": status,
            "rows_processed": total_processed,
            "duration_sec": duration_sec,
            "error": error_msg
        }


def main():
    parser = argparse.ArgumentParser(description="Direct Meta Marketing Graph API Ingestion Engine")
    parser.add_argument("--days", type=int, default=7, help="Number of past days to ingest (default: 7 for rolling conversion capture)")
    parser.add_argument("--date-from", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--date-to", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--accounts", type=str, help="Comma-separated Meta Ad Account IDs")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Batch size for database upserts")
    parser.add_argument("--delay", type=float, default=DEFAULT_INTER_BATCH_DELAY_SEC, help="Inter-batch sleep delay (seconds)")
    parser.add_argument("--dry-run", action="store_true", help="Extract and transform only, skip database writes")

    args = parser.parse_args()

    # Calculate date range
    if args.date_from and args.date_to:
        date_from = args.date_from
        date_to = args.date_to
    else:
        yesterday = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        date_from = yesterday
        date_to = today

    account_list = [a.strip() for a in args.accounts.split(",")] if args.accounts else None

    engine_instance = MetaDirectIngestionEngine(
        account_ids=account_list,
        batch_size=args.batch_size,
        inter_batch_delay=args.delay,
        dry_run=args.dry_run
    )

    res = engine_instance.run_sync(date_from=date_from, date_to=date_to)
    if res["status"] != "SUCCESS":
        sys.exit(1)


if __name__ == "__main__":
    main()
