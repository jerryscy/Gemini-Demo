#!/bin/bash
set -e

# Configuration
SERVICE_NAME="live-translation-public"
REGION="us-central1"
# Load from .env if present
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-winter-inkwell-390403}"

echo "===================================================="
echo "Deploying PUBLIC (unauthenticated) service..."
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
  --set-env-vars "ENABLE_OAUTH=false,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=global,IDLE_CLOSE_SECONDS=30"

echo "===================================================="
echo "Deployment Complete!"
echo "Your public service is available at the URL above."
echo "===================================================="
