#!/usr/bin/env bash
# =============================================================================
# setup.sh — Full GCP Infrastructure Setup for Dynamic Waste Reduction Engine
# Provisions: BigQuery, Vertex AI RAG, GCS, Pub/Sub, Artifact Registry
# =============================================================================
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

export PROJECT_ID="tcs-1770741130267"
export REGION="us-central1"
export BQ_DATASET="waste_engine"
export GCS_BUCKET="${PROJECT_ID}-waste-engine"
export SA_KEY_FILE="${PROJECT_ROOT}/tcs-1770741130267-a4a73ebadced.json"
export ARTIFACT_REPO="waste-engine"
export PUBSUB_TOPIC="waste-engine-events"
export PUBSUB_SUBSCRIPTION="waste-engine-sub"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[SETUP]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail() { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

# ── Pre-flight checks ─────────────────────────────────────────────────────────
log "Pre-flight checks..."
command -v gcloud >/dev/null 2>&1 || fail "gcloud CLI not found. Install from https://cloud.google.com/sdk"
command -v bq     >/dev/null 2>&1 || fail "bq CLI not found. Install gcloud SDK."
command -v gsutil >/dev/null 2>&1 || fail "gsutil not found. Install gcloud SDK."
command -v python3 >/dev/null 2>&1 || fail "python3 not found."
[[ -f "$SA_KEY_FILE" ]] || fail "Service account key not found at $SA_KEY_FILE"

# ── Authenticate ──────────────────────────────────────────────────────────────
log "Authenticating with service account..."
gcloud auth activate-service-account \
  --key-file="$SA_KEY_FILE" \
  --project="$PROJECT_ID"

gcloud config set project "$PROJECT_ID"
gcloud config set run/region "$REGION"
export GOOGLE_APPLICATION_CREDENTIALS="$SA_KEY_FILE"
log "Authenticated as: $(gcloud config get-value account)"

# ── Enable APIs ───────────────────────────────────────────────────────────────
log "Enabling required GCP APIs (this may take 2-3 minutes)..."
APIS=(
  "aiplatform.googleapis.com"
  "bigquery.googleapis.com"
  "bigquerystorage.googleapis.com"
  "run.googleapis.com"
  "pubsub.googleapis.com"
  "storage.googleapis.com"
  "storage-component.googleapis.com"
  "artifactregistry.googleapis.com"
  "dataflow.googleapis.com"
  "cloudbuild.googleapis.com"
  "iam.googleapis.com"
  "cloudresourcemanager.googleapis.com"
)
gcloud services enable "${APIS[@]}" --project="$PROJECT_ID"
log "All APIs enabled."

# ── Grant Service Account Roles ───────────────────────────────────────────────
log "Granting IAM roles to service account..."
SA_EMAIL="ai-engine-prod@${PROJECT_ID}.iam.gserviceaccount.com"
ROLES=(
  "roles/bigquery.admin"
  "roles/aiplatform.admin"
  "roles/storage.admin"
  "roles/pubsub.admin"
  "roles/run.admin"
  "roles/artifactregistry.admin"
  "roles/iam.serviceAccountUser"
)
for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$ROLE" \
    --quiet 2>/dev/null || warn "Role $ROLE may already be bound."
done
log "IAM roles granted."

# ── GCS Bucket ────────────────────────────────────────────────────────────────
log "Creating GCS bucket: gs://${GCS_BUCKET}"
if gsutil ls "gs://${GCS_BUCKET}" >/dev/null 2>&1; then
  warn "Bucket gs://${GCS_BUCKET} already exists."
else
  gsutil mb -l "$REGION" -p "$PROJECT_ID" "gs://${GCS_BUCKET}"
  log "Bucket created."
fi

# Create bucket directories
gsutil -q cp /dev/null "gs://${GCS_BUCKET}/rag-docs/.keep"
gsutil -q cp /dev/null "gs://${GCS_BUCKET}/model-artifacts/.keep"
gsutil -q cp /dev/null "gs://${GCS_BUCKET}/exports/.keep"

# Upload RAG documents
log "Uploading RAG knowledge documents to GCS..."
RAG_DOCS_DIR="${PROJECT_ROOT}/rag/documents"
if [[ -d "$RAG_DOCS_DIR" ]]; then
  gsutil -m cp "${RAG_DOCS_DIR}/"*.txt "gs://${GCS_BUCKET}/rag-docs/"
  log "RAG documents uploaded."
else
  warn "RAG documents directory not found at $RAG_DOCS_DIR"
fi

# ── BigQuery Dataset ──────────────────────────────────────────────────────────
log "Creating BigQuery dataset: ${PROJECT_ID}:${BQ_DATASET}"
if bq ls --project_id="$PROJECT_ID" "${BQ_DATASET}" >/dev/null 2>&1; then
  warn "Dataset ${BQ_DATASET} already exists."
else
  bq mk \
    --dataset \
    --location=US \
    --description="Dynamic Waste Reduction Engine — AI-powered perishable optimization data" \
    "${PROJECT_ID}:${BQ_DATASET}"
  log "Dataset created."
fi

# ── BigQuery Tables ───────────────────────────────────────────────────────────
log "Creating BigQuery tables..."
python3 "${SCRIPT_DIR}/create_bq_tables.py"
log "BigQuery tables created."

# ── Seed BigQuery with Inventory Data ─────────────────────────────────────────
log "Seeding BigQuery with initial inventory data..."
python3 "${SCRIPT_DIR}/seed_bigquery.py"
log "BigQuery seeded."

# ── Pub/Sub ───────────────────────────────────────────────────────────────────
log "Creating Pub/Sub topic: ${PUBSUB_TOPIC}"
if gcloud pubsub topics describe "$PUBSUB_TOPIC" --project="$PROJECT_ID" >/dev/null 2>&1; then
  warn "Topic ${PUBSUB_TOPIC} already exists."
else
  gcloud pubsub topics create "$PUBSUB_TOPIC" --project="$PROJECT_ID"
  log "Topic created."
fi

log "Creating Pub/Sub subscription: ${PUBSUB_SUBSCRIPTION}"
if gcloud pubsub subscriptions describe "$PUBSUB_SUBSCRIPTION" --project="$PROJECT_ID" >/dev/null 2>&1; then
  warn "Subscription already exists."
else
  gcloud pubsub subscriptions create "$PUBSUB_SUBSCRIPTION" \
    --topic="$PUBSUB_TOPIC" \
    --ack-deadline=60 \
    --project="$PROJECT_ID"
  log "Subscription created."
fi

# ── Artifact Registry ─────────────────────────────────────────────────────────
log "Creating Artifact Registry repository: ${ARTIFACT_REPO}"
if gcloud artifacts repositories describe "$ARTIFACT_REPO" \
    --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
  warn "Artifact Registry repo already exists."
else
  gcloud artifacts repositories create "$ARTIFACT_REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Waste Reduction Engine container images" \
    --project="$PROJECT_ID"
  log "Artifact Registry repository created."
fi

# ── Vertex AI RAG Corpus ──────────────────────────────────────────────────────
log "Setting up Vertex AI RAG corpus..."
python3 "${SCRIPT_DIR}/setup_rag.py"
log "Vertex AI RAG corpus ready."

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  GCP Infrastructure Setup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Project ID   : $PROJECT_ID"
echo "  Region       : $REGION"
echo "  BQ Dataset   : $BQ_DATASET"
echo "  GCS Bucket   : gs://$GCS_BUCKET"
echo "  Pub/Sub      : $PUBSUB_TOPIC"
echo "  Artifact Reg : ${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}"
echo ""
echo "  Next step: Run ./scripts/deploy.sh to build and deploy"
echo ""
