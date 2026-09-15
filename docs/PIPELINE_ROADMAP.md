# Nightly Marketing Pipeline — Roadmap to End-to-End

_Last updated: 2026-09-15. Companion to `MASTER_ROADMAP_AND_ARCHITECTURE.md`, whose Phase 4/5 items are marked complete but were never wired together end to end. This document tracks closing that loop._

## Where things stand

| Stage | Status | Reality |
|---|---|---|
| 1 · Meta ingestion → `raw_meta_ads_delivery` | ✅ Working | ~6 000 rows/day for 2 accounts. **Nothing reads this table yet.** |
| 2 · Cohort cache rebuild → `cohort_detail_cache` | ✅ Working (~5 min) | Sourced from legacy `facebookads`, not Stage 1. **The API does not read the cache** — `cohort_service.py` runs the live `COHORT_MASTER_OPTIMISED.sql` on every request. |
| 3 · Reconciliation | ⚠️ Reports only | Compared `raw_meta_ads_delivery` vs cache spend to $0.01; sources differ. Now a % tolerance and non-blocking (`RECONCILIATION_STRICT=false`). |
| 4 · Cache flush | ⚠️ Needs token | Now calls `POST /api/v1/internal/cache/clear` on the web service. Requires `PIPELINE_SERVICE_TOKEN` on both sides. |
| Scheduling | ⚠️ Duplicated | Cloud Scheduler → Cloud Run job at 02:30 UTC **and** GitHub Actions `daily-marketing-sync.yml` at 02:30 UTC over the public IP. |

Root causes fixed on 2026-09-14/15 (see git log): password masked by `str(URL)` in SQLAlchemy 2.x; phantom `sp_refresh_cohort_cache_nightly` procedure; `META_AD_ACCOUNT_IDS` dropped by `--set-env-vars`; 120 s read timeout on the cache rebuild; missing `data_pipeline_runs`, `raw_meta_ads_delivery`, `cohort_detail_cache` and the two `refresh_cohort_cache_*` procedures in production.

## Phase A — Stabilise the nightly job (this week, ~½ day)

Goal: the job goes green every night and the dashboard actually reflects it.

- [x] **A-1 Stage 3 non-blocking.** QC report is logged as a warning and the run continues; `RECONCILIATION_STRICT=true` re-arms the abort. Spend check uses `RECONCILIATION_SPEND_TOLERANCE_PCT` (default 5 %) and logs both figures.
- [x] **A-2 Stage 4 real flush.** `run_daily_pipeline.flush_backend_cache()` POSTs to `BACKEND_BASE_URL/api/v1/internal/cache/clear` with header `X-Pipeline-Token`. Fails soft.
  - [ ] Generate a token; store as Secret Manager `marketing-pipeline-token`; set `PIPELINE_SERVICE_TOKEN` in the web service's environment on Linode; redeploy both.
- [ ] **A-3 One scheduler.** Remove the `schedule:` trigger from `.github/workflows/daily-marketing-sync.yml` (keep `workflow_dispatch` for back-fills). Stop running production writes from a GitHub runner over the public IP; if the workflow is kept, route it through Cloud SQL Auth Proxy.
- [ ] **A-4 Alerting.** Cloud Monitoring alert on `run.googleapis.com/job/completed_execution_count{result="failed"}` → email/Slack.
- [ ] **A-5 Housekeeping.**
  - Apply `queries/01_production/01_apply_composite_indexes.sql` in a quiet window (adds `invoices.leads_contact_utm_id`; removes the last Stage 2 warning).
  - Audit the ~70 MySQL events on the instance for anything touching `cohort_detail_cache` / `facebookads`.
  - Rotate the DB password and Gemini key that were exposed in `.env`; add a new version to `marketing-db-pass`.
  - Set the GitHub `DB_USER` secret to `admin` (or remove the workflow's DB path per A-3).

## Phase B — Make the dashboard read the cache (next, ~1–2 days)

Goal: the sub-second dashboard promised by `28_nightly_cache.sql` ("STEP 5 · REPOINT THE CARDS" was never done).

- [ ] **B-1** `cohort_service` reads `cohort_detail_cache` for all cohort-window queries (Tabs 1–4). Keep the live master query behind `COHORT_LIVE_QUERY=true` for spot checks.
- [ ] **B-2 Freshness contract.** Expose `MAX(refreshed_at)` via `/api/v1/catalog`; show "Data as of …" in the UI; gate maturity windows on the refresh date, not `CURDATE()`.
- [ ] **B-3 Cache-vs-live test.** Assert equal totals for a fixed date using the reconcile query in `28_nightly_cache.sql` Step 3.
- [ ] **B-4 QC history.** Write Stage 3's report into `data_pipeline_runs` and surface the last result on the quality tab.

## Phase C — Cut over Meta delivery data to the new feed (~2–3 days)

Goal: Stage 1's data becomes the source of truth for spend/impressions/clicks; retire the `facebookads` dependency.

- [ ] **C-1 Repoint the procedure.** In `refresh_cohort_cache_one`, replace the `facebookads` CTE with an aggregate over `raw_meta_ads_delivery` at `date × campaign_id × ad_id` (collapse device/placement). Keep the `onlinecampaigns` campaign-code join.
- [ ] **C-2 Parallel run (7 days).** Stage 3 compares `facebookads` vs `raw_meta_ads_delivery` per campaign/day with a tolerance and reports drift.
- [ ] **C-3 Tab 5** (Meta Ads Manager view) reads `raw_meta_ads_delivery` directly for device/placement breakdowns.
- [ ] **C-4 Back-fill.** One `--date-from 2026-08-07 --mode full` run so the new feed covers the cache's history.
- [ ] **C-5 Retire** `facebookads` reads (`metadata.py`, the procedure) once drift is within tolerance for a week.

## Phase D — Hardening (background)

- [ ] Incremental cache rebuild: partition `cohort_detail_cache` by `cohort_days` + date and rebuild only immature windows (the "rolling 35 days" the script's docstring describes). Cuts Stage 2 from ~5 min to well under 1.
- [ ] Idempotency: record `execution_id` in `data_pipeline_runs`; skip Stage 2 if refreshed within N hours.
- [ ] `.dockerignore` for `.env` (build already honours `.gitignore`; make it explicit).
- [ ] Tests for tonight's failure modes: DB URL renders the real password; deploy script env list contains every key the code reads.

## Operating notes

- Deploy: `bash deploy_marketing_job.sh` (from a checkout at the intended commit — `git pull` first). `SKIP_BUILD=1` reuses the last image.
- Run now: `gcloud run jobs execute marketing-daily-sync --region asia-south1 --wait`
- Logs for the last execution:
  `gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="marketing-daily-sync"' --freshness=2h --order=asc --format='value(textPayload)' | grep -E 'STAGE|ERROR|WARNING|Failed|completed'`
- Watch Stage 2 progress: `SELECT cohort_days, COUNT(*) FROM cohort_detail_cache GROUP BY 1;`
