#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Build, push, and deploy the Waste Reduction Engine to Cloud Run
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

export PROJECT_ID="tcs-1770741130267"
export REGION="us-central1"
export ARTIFACT_REPO="waste-engine"
export SERVICE_NAME="waste-reduction-engine"
export SA_KEY_FILE="${PROJECT_ROOT}/tcs-1770741130267-a4a73ebadced.json"
export SA_EMAIL="ai-engine-prod@${PROJECT_ID}.iam.gserviceaccount.com"
export IMAGE="us-central1-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/api"
export TAG="${1:-latest}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[DEPLOY]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}   $*"; }
fail() { echo -e "${RED}[FAIL]${NC}   $*"; exit 1; }

# ── Pre-flight ────────────────────────────────────────────────────────────────
log "Pre-flight checks..."
command -v docker >/dev/null 2>&1 || fail "Docker not found."
command -v gcloud >/dev/null 2>&1 || fail "gcloud not found."
[[ -f "$SA_KEY_FILE" ]] || fail "Service account key not found."
[[ -f "${PROJECT_ROOT}/Dockerfile" ]] || fail "Dockerfile not found at project root."

# ── Authenticate ──────────────────────────────────────────────────────────────
log "Authenticating with service account..."
gcloud auth activate-service-account --key-file="$SA_KEY_FILE" --project="$PROJECT_ID"
gcloud config set project "$PROJECT_ID"
export GOOGLE_APPLICATION_CREDENTIALS="$SA_KEY_FILE"

# ── Configure Docker for Artifact Registry ────────────────────────────────────
log "Configuring Docker for Artifact Registry..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# ── Build Docker Image ────────────────────────────────────────────────────────
log "Building Docker image: ${IMAGE}:${TAG}"
cd "$PROJECT_ROOT"
docker build \
  --platform linux/amd64 \
  --build-arg PROJECT_ID="$PROJECT_ID" \
  --build-arg REGION="$REGION" \
  -t "${IMAGE}:${TAG}" \
  -t "${IMAGE}:latest" \
  -f Dockerfile \
  .
log "Build complete."

# ── Push to Artifact Registry ─────────────────────────────────────────────────
log "Pushing image to Artifact Registry..."
docker push "${IMAGE}:${TAG}"
[[ "$TAG" != "latest" ]] && docker push "${IMAGE}:latest"
log "Push complete."

# ── Read RAG Corpus name from env or file ─────────────────────────────────────
RAG_CORPUS_NAME=""
if [[ -f "${PROJECT_ROOT}/.rag_corpus_name" ]]; then
  RAG_CORPUS_NAME=$(cat "${PROJECT_ROOT}/.rag_corpus_name")
fi

# ── Deploy to Cloud Run ───────────────────────────────────────────────────────
log "Deploying to Cloud Run: ${SERVICE_NAME} (${REGION})..."
gcloud run deploy "$SERVICE_NAME" \
  --image="${IMAGE}:${TAG}" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=80 \
  --timeout=300 \
  --service-account="$SA_EMAIL" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --set-env-vars="GOOGLE_CLOUD_LOCATION=${REGION}" \
  --set-env-vars="BQ_DATASET=waste_engine" \
  --set-env-vars="BQ_TABLE=inventory" \
  --set-env-vars="GCS_BUCKET=${PROJECT_ID}-waste-engine" \
  --set-env-vars="RAG_CORPUS_NAME=${RAG_CORPUS_NAME}" \
  --set-env-vars="PUBSUB_TOPIC=waste-engine-events" \
  --set-env-vars="DEMO_MODE=false" \
  --set-env-vars="GOOGLE_API_KEY=AIzaSyAnN2SdnVP8L5F_lv-SjymXGtfPIY58HFs" \
  --set-secrets="GOOGLE_APPLICATION_CREDENTIALS_JSON=waste-engine-sa-key:latest" \
  --project="$PROJECT_ID"

# ── Get Service URL ───────────────────────────────────────────────────────────
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region="$REGION" \
  --format="value(status.url)" \
  --project="$PROJECT_ID")

log "Deployment complete!"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Deployment Successful!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Service URL  : $SERVICE_URL"
echo "  Image        : ${IMAGE}:${TAG}"
echo "  Region       : $REGION"
echo ""
echo "  Health check : ${SERVICE_URL}/health"
echo "  Demo         : ${SERVICE_URL}/"
echo "  API docs     : ${SERVICE_URL}/api/v1/docs"
echo ""

# ── Smoke test ────────────────────────────────────────────────────────────────
log "Running smoke test..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/health" || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
  log "Smoke test PASSED (HTTP 200)"
else
  warn "Smoke test returned HTTP $HTTP_CODE — check Cloud Run logs."
fi
