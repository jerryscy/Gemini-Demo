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
DEFAULT_MODE="translation"
DEFAULT_SOURCE_LANG="Chinese (Simplified)"
DEFAULT_SOURCE_LANG_CODE="zh-Hans"
DEFAULT_TARGET_LANG="English"
DEFAULT_TARGET_LANG_CODE="en"
IDLE_CLOSE_SECONDS="30"
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

1. **Mode Selector**:
   - **Live Translation** (`gemini-3.5-live-translate-preview`): Translates spoken audio to the chosen target language with real-time text and synthesized 24 kHz voice audio.
   - **Live Transcription** (`gemini-3.5-transcribe-live-preview`): Real-time speech-to-text transcription. Target language selection and audio output are automatically disabled in this mode.
2. **Language Configuration**:
   - Select one or multiple input languages (e.g. `zh-Hans`, `en`).
   - Select target output language (78 supported BCP-47 standard languages).
3. **Recording & Audio**:
   - Click **▶ Start** and grant microphone permissions.
   - Left column displays source speech transcription (type 1).
   - Right column displays translated text (type 2).
   - The **Play audio** toggle enables/disables real-time translated voice playback.

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
- `uid`: Unique client session ID generated per browser connection.
- `seq`: Turn sequence counter that increments on turn completion.
- `type`: `1` for source input transcript, `2` for translation.
- `delta` / `text`: Incremental text chunk or cumulative transcript string.
- `finished`: `false` while streaming, `true` when turn is complete.

### Binary Messages
- **Client $\rightarrow$ Server**: 16 kHz 16-bit linear PCM microphone chunks (~100ms).
- **Server $\rightarrow$ Client**: 24 kHz 16-bit linear PCM translated audio chunks.

---

## 6. Session Lifecycle & Keep-Alive

- Clicking **Stop** pauses audio transmission but retains the Live API session in an idle state.
- Clicking **Start** within `IDLE_CLOSE_SECONDS` (default: 30s) resumes streaming instantly without reconnecting.
- If idle beyond `IDLE_CLOSE_SECONDS`, the session is cleanly closed to prevent unnecessary billing, and the next **Start** automatically reconnects.
