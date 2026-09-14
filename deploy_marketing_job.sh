#!/usr/bin/env bash
# =============================================================================
# deploy_marketing_job.sh
# Creates/updates the Cloud Run Job and Cloud Scheduler triggers for Marketing Pipeline
# Standardized to match Bambinos CML GCP infrastructure (asia-south1, Cloud SQL).
# Usage: bash deploy_marketing_job.sh [--dry-run]
# =============================================================================
set -euo pipefail

# ─── CONFIG ──────────────────────────────────────────────────────────────────
PROJECT="bambinos-411405"
REGION="asia-south1"
REPO="marketing-dashboard"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/app:latest"
ENV_FILE="$(dirname "$0")/cron-marketing-env.yaml"

CLOUD_SQL_INSTANCE="${PROJECT}:${REGION}:production"
PROJECT_NUM="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)' 2>/dev/null || echo "1045498615373")"
SCHEDULER_SA="${PROJECT_NUM}-compute@developer.gserviceaccount.com"
NETWORK="default"
SUBNET="default"
VPC_EGRESS="private-ranges-only"
MAX_RETRIES=0
TIMEOUT="30m"
JOB_NAME="marketing-daily-sync"
SCHEDULE_CRON="30 2 * * *"  # 08:00 AM IST (02:30 UTC)
TIMEZONE="Asia/Kolkata"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

run() {
  if $DRY_RUN; then
    echo "  [DRY RUN] $*"
  else
    "$@"
  fi
}

echo "======================================================================"
echo "🚀 Deploying Marketing Data Pipeline to GCP Cloud Run & Cloud Scheduler"
echo "Project: $PROJECT | Region: $REGION | Job: $JOB_NAME"
echo "======================================================================"

# ─── 1. ARTIFACT REGISTRY ────────────────────────────────────────────────────
echo ""
echo "━━━ 1. Artifact Registry ━━━"
if ! gcloud artifacts repositories describe "$REPO" --location "$REGION" --project "$PROJECT" &>/dev/null; then
  echo "  + creating repository $REPO"
  run gcloud artifacts repositories create "$REPO" \
    --repository-format=docker --location "$REGION" --project "$PROJECT" \
    --description="Cohort Marketing Intelligence unified container"
else
  echo "  ✓ repository $REPO exists"
fi

# ─── 2. BUILD IMAGE ──────────────────────────────────────────────────────────
echo ""
echo "━━━ 2. Build image ━━━"
if [[ "${SKIP_BUILD:-0}" == "1" ]]; then
  echo "  SKIP_BUILD=1 — using already-pushed $IMAGE"
else
  echo "  $IMAGE"
  run gcloud builds submit --tag "$IMAGE" --project "$PROJECT" "$(dirname "$0")"
fi

# ─── 3. CLOUD RUN JOB ────────────────────────────────────────────────────────
echo ""
echo "━━━ 3. Deploy Cloud Run Job: $JOB_NAME ━━━"

CMD="create"
if gcloud run jobs describe "$JOB_NAME" --region "$REGION" --project "$PROJECT" &>/dev/null; then
  CMD="update"
fi

args_arr=(
  "run" "jobs" "$CMD" "$JOB_NAME"
  "--image" "$IMAGE"
  "--command" "python"
  "--args" "backend/scripts/run_daily_pipeline.py"
  "--tasks" "1"
  "--region" "$REGION"
  "--project" "$PROJECT"
  "--set-cloudsql-instances" "$CLOUD_SQL_INSTANCE"
  "--set-secrets" "DB_PASS=cron-transcript-db-pass:latest,META_ACCESS_TOKEN=metaAccessToken:latest"
  "--network" "$NETWORK"
  "--subnet" "$SUBNET"
  "--vpc-egress" "$VPC_EGRESS"
  "--max-retries" "$MAX_RETRIES"
  "--task-timeout" "$TIMEOUT"
  "--cpu" "1"
  "--memory" "2Gi"
  "--set-env-vars" "DB_SOCKET=/cloudsql/${CLOUD_SQL_INSTANCE},DB_USER=root,DB_NAME=production,DB_READ_ONLY=false,TZ=Asia/Kolkata,META_API_VERSION=v20.0"
)

run gcloud "${args_arr[@]}"

# ─── 4. CLOUD SCHEDULER TRIGGER (08:00 AM IST) ───────────────────────────────
SCHEDULER_JOB="${JOB_NAME}-trigger"
echo ""
echo "━━━ 4. Configure Cloud Scheduler: $SCHEDULER_JOB ($SCHEDULE_CRON $TIMEZONE) ━━━"

SCHED_CMD="create"
if gcloud scheduler jobs describe "$SCHEDULER_JOB" --location "$REGION" --project "$PROJECT" &>/dev/null; then
  SCHED_CMD="update"
fi

sched_arr=(
  "scheduler" "jobs" "$SCHED_CMD" "http" "$SCHEDULER_JOB"
  "--location" "$REGION"
  "--project" "$PROJECT"
  "--schedule" "$SCHEDULE_CRON"
  "--time-zone" "$TIMEZONE"
  "--uri" "https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB_NAME}:run"
  "--oauth-service-account-email" "$SCHEDULER_SA"
)

run gcloud "${sched_arr[@]}"

echo ""
echo "======================================================================"
echo "✅ Marketing Data Pipeline Job & Cloud Scheduler Successfully Deployed!"
echo "======================================================================"
