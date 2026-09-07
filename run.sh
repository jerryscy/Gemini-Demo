#!/usr/bin/env bash
# Launch the Gemini Live Translation / Transcription application.
set -euo pipefail
cd "$(dirname "$0")"

APP_PY="./.venv-app/bin/python"
if [ ! -x "$APP_PY" ]; then
    APP_PY="python3"
fi

export PYTHONUNBUFFERED=1

echo "Starting Gemini Live app on http://127.0.0.1:8000"
exec "$APP_PY" -m uvicorn main:app --host 127.0.0.1 --port 8000
