#!/usr/bin/env bash
# ==============================================================================
# Cloud Run Deployment Script for Gemini Live Translation & Transcription
# ==============================================================================
set -euo pipefail

# 1. Load environment variables from .env if present
if [ -f .env ]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

# 2. Configuration & Defaults
SERVICE_NAME="${SERVICE_NAME:-live-translation}"
REGION="${GOOGLE_CLOUD_REGION:-${REGION:-us-central1}}"
GCLOUD_CONFIG="${GCLOUD_CONFIG:-}"

# Resolve GCP Project ID
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}"
if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
  echo "Error: No Google Cloud project configured."
  echo "Please set GOOGLE_CLOUD_PROJECT in your .env file or run: gcloud config set project <PROJECT_ID>"
  exit 1
fi

IDLE_CLOSE_SECONDS="${IDLE_CLOSE_SECONDS:-600}"
DEFAULT_MODE="${DEFAULT_MODE:-transcription}"
LIVE_API_MODEL="${LIVE_API_MODEL:-gemini-3.5-transcribe-live-preview}"
ENABLE_OAUTH="${ENABLE_OAUTH:-false}"

# Build gcloud base command (with optional --configuration flag)
GCLOUD_CMD=(gcloud)
if [ -n "$GCLOUD_CONFIG" ]; then
  GCLOUD_CMD+=(--configuration="$GCLOUD_CONFIG")
fi

echo "=================================================================="
echo " Deploying Gemini Live Application to Cloud Run"
echo "=================================================================="
echo " Service Name: $SERVICE_NAME"
echo " Project ID:   $PROJECT_ID"
echo " Region:       $REGION"
echo " Default Mode: $DEFAULT_MODE ($LIVE_API_MODEL)"
echo " Session Idle: ${IDLE_CLOSE_SECONDS}s (10 min session cap)"
echo " OAuth Auth:   $ENABLE_OAUTH"
echo "=================================================================="

# Base environment variables for Cloud Run container
ENV_VARS=(
  "GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
  "GOOGLE_CLOUD_LOCATION=global"
  "DEFAULT_MODE=$DEFAULT_MODE"
  "LIVE_API_MODEL=$LIVE_API_MODEL"
  "TRANSLATION_MODEL_ID=${TRANSLATION_MODEL_ID:-gemini-3.5-live-translate-preview}"
  "TRANSCRIPTION_MODEL_ID=${TRANSCRIPTION_MODEL_ID:-gemini-3.5-transcribe-live-preview}"
  "IDLE_CLOSE_SECONDS=$IDLE_CLOSE_SECONDS"
  "ENABLE_OAUTH=$ENABLE_OAUTH"
)

# If OAuth is enabled, ensure required variables are set
if [ "$ENABLE_OAUTH" = "true" ]; then
  if [ -z "${GOOGLE_CLIENT_ID:-}" ] || [ -z "${GOOGLE_CLIENT_SECRET:-}" ]; then
    echo "Error: OAuth is enabled (ENABLE_OAUTH=true) but GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is missing."
    exit 1
  fi
  ENV_VARS+=(
    "GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID"
    "GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET"
    "SESSION_SECRET_KEY=${SESSION_SECRET_KEY:-$(openssl rand -hex 32 2>/dev/null || echo 'default-random-secret-key-32b')}"
    "ALLOWED_EMAILS=${ALLOWED_EMAILS:-}"
  )
fi

# Join environment variables with comma
ENV_VARS_STR=$(IFS=,; echo "${ENV_VARS[*]}")

# Deploy to Cloud Run
"${GCLOUD_CMD[@]}" run deploy "$SERVICE_NAME" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --source=. \
  --allow-unauthenticated \
  --set-env-vars="$ENV_VARS_STR" \
  --quiet

echo "=================================================================="
echo " Deployment Complete!"
echo " Service URL: $("${GCLOUD_CMD[@]}" run services describe "$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')"
echo "=================================================================="
