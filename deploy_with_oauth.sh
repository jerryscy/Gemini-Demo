#!/usr/bin/env bash
set -euo pipefail

# Configuration
SERVICE_NAME="${SERVICE_NAME:-live-translation}"
REGION="${GOOGLE_CLOUD_REGION:-${REGION:-us-central1}}"
GCLOUD_CONFIG="${GCLOUD_CONFIG:-}"

# Load from .env if present
if [ -f .env ]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}"
if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
  echo "Error: No Google Cloud project configured."
  echo "Please set GOOGLE_CLOUD_PROJECT in your .env file or run: gcloud config set project <PROJECT_ID>"
  exit 1
fi

GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-}"
GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-}"
SESSION_SECRET_KEY="${SESSION_SECRET_KEY:-$(openssl rand -hex 32 2>/dev/null || echo 'default-random-secret-key-32b')}"
ALLOWED_EMAILS="${ALLOWED_EMAILS:-}"
IDLE_CLOSE_SECONDS="${IDLE_CLOSE_SECONDS:-600}"

if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ]; then
  echo "Error: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is missing."
  echo "Please provide them in .env or as environment variables."
  exit 1
fi

echo "===================================================="
echo "Deploying SECURE (OAuth authenticated) service..."
echo "Service: $SERVICE_NAME"
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo "===================================================="

GCLOUD_CMD=(gcloud)
if [ -n "$GCLOUD_CONFIG" ]; then
  GCLOUD_CMD+=(--configuration="$GCLOUD_CONFIG")
fi

# Deploy to Cloud Run
"${GCLOUD_CMD[@]}" run deploy "$SERVICE_NAME" \
  --project="$PROJECT_ID" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "ENABLE_OAUTH=true,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=global,DEFAULT_MODE=transcription,LIVE_API_MODEL=gemini-3.5-transcribe-live-preview,GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET,SESSION_SECRET_KEY=$SESSION_SECRET_KEY,ALLOWED_EMAILS=$ALLOWED_EMAILS,IDLE_CLOSE_SECONDS=$IDLE_CLOSE_SECONDS" \
  --quiet

echo "===================================================="
echo "Deployment Complete!"
SERVICE_URL="$("${GCLOUD_CMD[@]}" run services describe "$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')"
echo "Your authenticated service is available at: $SERVICE_URL"
echo "IMPORTANT: Register the redirect URI in Google Cloud Console:"
echo "   https://console.cloud.google.com/apis/credentials"
echo "   Authorized redirect URI: ${SERVICE_URL}/callback"
echo "===================================================="
