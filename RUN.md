# Running the Gemini Live Application

This application runs as a **single-process** FastAPI + WebSocket service powered by Google's **Gemini 3.5 Live API** (`google-genai` SDK with `enterprise=True` on Vertex AI).

| Component | Technology | Description | Port |
|---|---|---|---|
| **Web Service & Worker** | Python ≥3.10 (`.venv-app`) | FastAPI, WebSockets, `google-genai` SDK | `8000` |
| **Frontend** | Vanilla JS / Web Audio | AudioWorklet capture (16 kHz) & 24 kHz playback | — |

---

## 1. Authenticate to Google Cloud (Required)

Ensure your gcloud CLI is authenticated with Application Default Credentials:

```bash
gcloud auth application-default login
```

Set your GCP project ID and region in `.env`.
> **Note**: Both `gemini-3.5-live-translate-preview` and `gemini-3.5-transcribe-live-preview` require `GOOGLE_CLOUD_LOCATION="global"`.

---

## 2. Environment Setup

Create and activate a Python virtual environment (Python ≥3.10):

```bash
python3 -m venv .venv-app
./.venv-app/bin/pip install --index-url https://pypi.org/simple -r requirements.txt
```

Copy the example environment configuration:

```bash
cp .env.example .env
```

Ensure `.env` contains:
```env
GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
GOOGLE_CLOUD_LOCATION="global"
TRANSLATION_MODEL_ID="gemini-3.5-live-translate-preview"
TRANSCRIPTION_MODEL_ID="gemini-3.5-transcribe-live-preview"
DEFAULT_MODE="transcription"
LIVE_API_MODEL="gemini-3.5-transcribe-live-preview"
DEFAULT_SOURCE_LANG="Chinese (Simplified)"
DEFAULT_SOURCE_LANG_CODE="zh-Hans"
DEFAULT_TARGET_LANG="English"
DEFAULT_TARGET_LANG_CODE="en"
IDLE_CLOSE_SECONDS="600"
DEBUG_LIVE_API="false"
```

---

## 3. Start the Application

Start the server using `run.sh` or directly with uvicorn:

```bash
./run.sh
```

Or:

```bash
./.venv-app/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

> **Tip**: If port 8000 is occupied, free it with:
> `kill -9 $(lsof -tiTCP:8000) 2>/dev/null || true`

---

## 4. Using the Web Interface

Open **`http://127.0.0.1:8000`** in your browser (Chrome or Edge recommended):

1. **Auto-Connect & Recording**:
   - The page automatically connects to the server and Gemini Live API upon loading.
   - Microphone capture starts immediately, and the 10-minute session countdown timer (`10:00`) starts ticking down.
2. **Mode Selector**:
   - **Live Transcription (Default)** (`gemini-3.5-transcribe-live-preview`): Real-time speech-to-text transcription. The unified result card displays source transcriptions.
   - **Live Translation** (`gemini-3.5-live-translate-preview`): Translates spoken audio to the chosen target language with real-time text and synthesized 24 kHz voice audio.
   - *Switching tabs automatically clears previous content and reconnects the Live session with the corresponding model.*
3. **Language Configuration**:
   - Select one or multiple input languages (e.g. `zh-Hans`, `en`).
   - Select target output language (active in Translation mode).
4. **`↻ Reset` Button**:
   - Click **`↻ Reset`** to disconnect the existing session, clear previous transcripts, reset the countdown timer back to `10:00`, and start a fresh session immediately.
5. **10-Minute Expiry**:
   - Sessions are capped at 10 minutes to respect Gemini Live API limits. When 10 minutes expire, the timer displays `00:00 (10m Due)` and terminates the connection. Click **`↻ Reset`** to initiate a new session.

---

## 5. Data Contract (`ws://127.0.0.1:8000/ws`)

### Text Messages (`{"kind": "data", "data": {...}}`)
```json
{
  "uid": "uuid-string",
  "seq": 1,
  "type": 1,
  "delta": "Partial transcript chunk",
  "finished": false
}
```
- `uid`: Unique client session ID generated per session.
- `seq`: Turn sequence counter that increments on turn completion.
- `type`: `1` for source input transcript, `2` for translation.
- `delta` / `text`: Incremental text chunk or cumulative transcript string.
- `finished`: `false` while streaming, `true` when turn is complete.

### Binary Messages
- **Client $\rightarrow$ Server**: 16 kHz 16-bit linear PCM microphone chunks (~100ms).
- **Server $\rightarrow$ Client**: 24 kHz 16-bit linear PCM translated audio chunks (Translation mode only).

---

## 6. Session Lifecycle & Watchdog

- **10-Minute Hard Cap**: `liveapiworker.py` and frontend both enforce a 600-second (10-minute) session lifetime.
- **Auto-Termination**: At 600 seconds, the backend closes the Live API receiver and client displays `00:00 (10m Due)`.
- **Reset**: Clicking **`↻ Reset`** calls `worker.reset_session()`, discarding queues and reconnecting to Gemini Live API with a fresh session UID and timer.

---

## 7. Cloud Run Deployment

Deploy with one command using the provided scripts:

```bash
# Public deployment
./deploy.sh

# Or unauthenticated public
./deploy_no_auth.sh

# Or OAuth protected
./deploy_with_oauth.sh
```

