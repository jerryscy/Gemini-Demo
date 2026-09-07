#!/bin/bash
set -e

# Configuration
SERVICE_NAME="live-translation-oauth"
REGION="us-central1"
PROJECT_ID="winter-inkwell-390403"

# Load from .env if present
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-}"
GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-}"
SESSION_SECRET_KEY="${SESSION_SECRET_KEY:-}"
ALLOWED_EMAILS="${ALLOWED_EMAILS:-}"

echo "===================================================="
echo "Deploying SECURE (OAuth authenticated) service..."
echo "Service: $SERVICE_NAME"
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo "===================================================="

# Check if logged in / project exists
gcloud --configuration=argolis config set project "$PROJECT_ID"

# Deploy to Cloud Run
# Using --source . compiles and deploys the container in one step
gcloud --configuration=argolis run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "ENABLE_OAUTH=true,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=global,GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET,SESSION_SECRET_KEY=$SESSION_SECRET_KEY,ALLOWED_EMAILS=$ALLOWED_EMAILS,IDLE_CLOSE_SECONDS=30"

echo "===================================================="
echo "Deployment Complete!"
echo "Your authenticated service is available at the URL above."
echo "IMPORTANT: Make sure to register the redirect URI in Google Cloud Console:"
echo "   https://console.cloud.google.com/apis/credentials"
echo "   Authorized redirect URI: <SERVICE_URL>/callback"
echo "===================================================="
