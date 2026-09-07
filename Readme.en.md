# 🎙️ Real-Time Audio Translation & Transcription · Gemini 3.5 Live API

[![zh](https://img.shields.io/badge/lang-中文-red.svg)](./Readme.md)
[![en](https://img.shields.io/badge/lang-English-blue.svg)](./Readme.en.md)

> A high-performance real-time speech translation and transcription application powered by Google's **Gemini 3.5 Live API** on Vertex AI (`google-genai` SDK). Microphone audio is captured in the browser and streamed to the backend via WebSockets → processed directly with Gemini Live models (`gemini-3.5-live-translate-preview` for speech-to-speech translation or `gemini-3.5-transcribe-live-preview` for live speech-to-text) → and the **source transcript**, **translated transcript**, and **synthesized voice audio** stream back to the browser in real time.

---

## 📑 Table of Contents

- [✨ Features](#-features)
- [🧭 How It Works](#-how-it-works)
- [🏗️ Architecture](#️-architecture)
- [✅ Prerequisites](#-prerequisites)
- [⚡ Quick Start](#-quick-start)
- [🔐 Configuration & Authentication](#-configuration--authentication)
- [🚀 Running & Usage](#-running--usage)
- [📦 Data Contract](#-data-contract)
- [🧠 Key Live API Configuration](#-key-live-api-configuration)
- [☁️ Cloud Run Deployment](#️-cloud-run-deployment)
- [🛠️ Troubleshooting](#️-troubleshooting)

---

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🔀 | **Mode Selector** | Toggle between **Live Translation** (`gemini-3.5-live-translate-preview`) and **Live Transcription** (`gemini-3.5-transcribe-live-preview`) |
| 🎤 | **Real-time audio streaming** | MediaStream API + AudioWorklet captures mic audio at 16 kHz mono PCM in clean 100ms packets |
| 🌍 | **78 Languages** | Full Gemini 3.5 Live language catalog using standard BCP-47 codes (e.g., `zh-Hans`, `zh-Hant`, `en`, `es`, `ja`) |
| 🌐 | **Multi-Language Input Detection** | Select one or multiple source languages for speech recognition and language identification |
| 🗣️ | **Translated Speech Playback** | 24 kHz 16-bit linear PCM audio streamed to the browser with Web Audio API playback |
| 🔒 | **Context-Aware UI Controls** | Target language and speech playback options automatically disable when Live Transcription is active |
| 🎧 | **Browser Echo/Noise Suppression** | Built-in browser `echoCancellation`, `noiseSuppression`, and `autoGainControl` minimize feedback and distortion |
| 🎭 | **Affective Dialog & Voice Options** | Synthesized translations mirror speaker emotion via `enable_affective_dialog` |
| ⏱️ | **Server-side VAD** | Automatic voice activity detection with tuned sensitivity for low-latency interpretation |
| 🚦 | **No Mid-Turn Interruption** | `activity_handling = NO_INTERRUPTION` prevents background audio from truncating in-progress translations |
| 🧠 | **Context Window Compression** | Sliding token window prevents session drops during extended conversations |
| 🔌 | **Live Connection Indicator** | Real-time status badge showing Browser ↔ Backend ↔ Live API states |
| ⏸️ | **Instant Resume on Stop/Start** | Stopping pauses audio while preserving the active session; resumes instantly without reconnect delays |
| 🎨 | **Zero-Build Frontend** | Clean, responsive UI built with vanilla JavaScript and modern CSS (no bundlers required) |

---

## 🧭 How It Works

```
🎙️ Microphone
   │  16 kHz mono PCM (100ms chunks)
   ▼
🌐 Browser (AudioWorklet)          ── 32-bit float → 16-bit PCM
   │                                   mic constraints: echoCancellation / noiseSuppression / autoGainControl
   │  WebSocket (binary PCM audio + JSON control messages)
   ▼
⚙️  FastAPI backend (main.py)       ── Two-way message router
   │     ├─ audio chunks → LiveAPIWorker.send_audio_data()
   │     └─ start/stop/mode/language controls → LiveAPIWorker lifecycle
   ▼
🤖 LiveAPIWorker (liveapiworker.py) ── Live API session manager (Vertex AI enterprise=True)
   │
   ├── [Mode: Translation]   ── gemini-3.5-live-translate-preview (Source STT + Translation + Audio)
   └── [Mode: Transcription] ── gemini-3.5-transcribe-live-preview (Source STT)
   │
   │  WebSocket return stream
   ▼
🌐 Browser (index.html)             ── Renders real-time text + plays 24 kHz audio via Web Audio API
```

### Step-by-Step Flow

1. **Audio Capture**: The browser accesses the microphone at 16 kHz mono with hardware echo cancellation, noise suppression, and auto gain control.
2. **Chunking & Quantization**: `AudioWorklet` (with inline Blob fallback) buffers 100ms of audio (1,600 samples) and converts 32-bit float samples to 16-bit linear PCM.
3. **Session Signaling**: Pressing **Start** initializes the WebSocket session and triggers `LiveAPIWorker` to establish a persistent connection with Google's Gemini Live API.
4. **Vertex AI Processing**: Audio is streamed in real time to the selected Gemini 3.5 model in the `global` region.
5. **Streamed Return**: The backend receives translated audio and synchronized transcription deltas, forwarding them immediately to the browser.
6. **Playback & Rendering**: The frontend accumulates text deltas into chat bubbles and decodes/schedules 24 kHz audio buffers for seamless audio playback.

---

## 🏗️ Architecture

The application runs as a lightweight, single-process service:

| Component | Technology | Key Files | Description |
|---|---|---|---|
| **Frontend** | Vanilla JS · Web Audio API · AudioWorklet | `static/index.html`, `static/audio-processor.js` | Audio capture, delta assembly, 24 kHz playback |
| **Backend Router** | Python ≥3.10 · FastAPI · WebSockets | `main.py` | HTTP static file serving, WebSocket endpoint, auth |
| **Live Worker** | `google-genai` (SDK ≥2.22.0) | `liveapiworker.py` | Vertex AI Live API connection, session lifecycle |
| **Language Metadata** | Python dictionary & BCP-47 codes | `languages.py` | 78 supported Gemini 3.5 Live languages |
| **AI Models** | Vertex AI (`enterprise=True`) | Google Gemini Live API | `gemini-3.5-live-translate-preview`<br>`gemini-3.5-transcribe-live-preview` |

---

## ✅ Prerequisites

- **Python 3.10+** (tested up to Python 3.14)
- **Google Cloud SDK (`gcloud`)** installed and authenticated
- **A GCP Project with Vertex AI API enabled**
- **Modern Web Browser** with microphone support (Google Chrome or Microsoft Edge recommended)

---

## ⚡ Quick Start

```bash
# 1. Clone repository
git clone https://github.com/jerryscy/Live-translation-with-Gemini-Live-API-Native-Audio.git
cd Live-translation-with-Gemini-Live-API-Native-Audio

# 2. Create virtual environment & install dependencies
python3 -m venv .venv-app
./.venv-app/bin/pip install --index-url https://pypi.org/simple -r requirements.txt

# 3. Configure environment
cp .env.example .env

# 4. Authenticate with Google Cloud
gcloud auth application-default login

# 5. Start the application
./run.sh
```

Open your browser at **`http://127.0.0.1:8000`**.

---

## 🔐 Configuration & Authentication

### 1. Environment Variables (`.env`)

Configure your project and preferences in `.env`:

```env
# Google Cloud / Vertex AI settings
GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
GOOGLE_CLOUD_LOCATION="global"  # Gemini 3.5 Live models require "global"

# Models and Mode
TRANSLATION_MODEL_ID="gemini-3.5-live-translate-preview"
TRANSCRIPTION_MODEL_ID="gemini-3.5-transcribe-live-preview"
DEFAULT_MODE="translation"

# Default Languages (BCP-47)
DEFAULT_SOURCE_LANG="Chinese (Simplified)"
DEFAULT_SOURCE_LANG_CODE="zh-Hans"
DEFAULT_TARGET_LANG="English"
DEFAULT_TARGET_LANG_CODE="en"

# Session Lifecycle
IDLE_CLOSE_SECONDS="30"  # Keep-alive window when paused before disconnecting
DEBUG_LIVE_API="false"   # Set to true for verbose Live API timing logs
```

### 2. Google Cloud Authentication

Authenticate your local environment with Application Default Credentials (ADC):

```bash
gcloud auth application-default login
gcloud config set project your-gcp-project-id
```

---

## 🚀 Running & Usage

Start with the runner script:
```bash
./run.sh
```

Or run directly with `uvicorn`:
```bash
./.venv-app/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Web Interface Guide

1. **Select Mode**:
   - **Live Translation**: Speaks and translates input into the target language.
   - **Live Transcription**: Transcribes speech into text without translation or audio synthesis.
2. **Configure Languages**:
   - **Input Language**: Check one or more source languages (e.g. `zh-Hans`, `en`).
   - **Target Language**: Select output language (active in Translation mode).
3. **Start Translating**:
   - Click **▶ Start** and speak into your microphone.
   - View real-time source text (left column) and translation (right column).
   - Toggle **Play audio** to hear translated speech.
4. **Pause and Resume**:
   - Click **⏹ Stop** to pause audio transmission.
   - Click **▶ Start** within 30 seconds to resume immediately without waiting for a new connection.

---

## 📦 Data Contract

Client and server communicate over WebSocket (`ws://127.0.0.1:8000/ws`):

### Text Messages (`{"kind": "data", "data": {...}}`)

```json
{
  "uid": "917289fa-4e13-492e-af0c-b33189798dae",
  "seq": 1,
  "type": 2,
  "delta": " The weather is very nice today.",
  "finished": false
}
```

| Field | Type | Description |
|---|---|---|
| `uid` | string | Unique client session identifier generated per connection |
| `seq` | integer | Turn counter; increments sequentially on each finished utterance |
| `type` | integer | `1` = Source transcription, `2` = Translated text |
| `delta` | string | Incremental text chunk received from Gemini Live API |
| `finished` | boolean | `false` while speaker turn is active, `true` upon completion |

### Binary Messages
- **Upstream (Client $ightarrow$ Server)**: 16 kHz 16-bit linear PCM microphone chunks (~100ms).
- **Downstream (Server $ightarrow$ Client)**: 24 kHz 16-bit linear PCM translated speech audio chunks.

---

## 🧠 Key Live API Configuration

`LiveAPIWorker` configures the session specifically for low-latency interpretation:

| Setting | Configuration | Purpose |
|---|---|---|
| `client` | `genai.Client(vertexai=True, enterprise=True, location="global")` | Connects to Vertex AI Gemini 3.5 Live endpoint |
| `response_modalities` | `["AUDIO"]` | Receives synthesized speech audio alongside transcripts |
| `translation_config` | `target_language`, `echo_target_language=False` | Configures target language; model remains silent if input matches target |
| `input_audio_transcription` | `AudioTranscriptionConfig()` | Server-side automated speech-to-text with language ID |
| `output_audio_transcription` | `AudioTranscriptionConfig()` | Synchronized transcript of generated speech output |
| `activity_handling` | `NO_INTERRUPTION` | Prevents subsequent speech from cutting off in-progress translations |
| `proactivity` | `proactive_audio=True` | Starts streaming speech translation as soon as sentence context allows |
| `voice_config` | `prebuilt_voice_config={"voice_name": "puck"}` | 24 kHz natural voice synthesis |

---

## ☁️ Cloud Run Deployment

Deployment helper scripts are provided in the repository:

- **Public deployment (No OAuth)**:
  ```bash
  ./deploy_no_auth.sh
  ```
- **Protected deployment with Google OAuth**:
  ```bash
  ./deploy_with_oauth.sh
  ```

---

## 🛠️ Troubleshooting

<details>
<summary><strong>🔑 Authentication & Quota Issues</strong></summary>

- Run `gcloud auth application-default login` to refresh credentials.
- Ensure your project has the **Vertex AI API** enabled.
- Verify `GOOGLE_CLOUD_LOCATION="global"` in `.env` (Gemini 3.5 Live models are only available in `global`).
</details>

<details>
<summary><strong>🎤 Microphone & AudioWorklet Errors</strong></summary>

- Grant microphone permission in your browser (`chrome://settings/content/microphone`).
- `AudioWorklet` requires a secure context (`https://` or `http://localhost` / `http://127.0.0.1`).
- The application automatically falls back to an inlined Blob URL if external worklet scripts are blocked.
</details>

<details>
<summary><strong>🔇 No Audio Output During Translation</strong></summary>

- Ensure **Play audio** is toggled ON in the UI.
- Web browsers suspend audio contexts until the user clicks an element; clicking **▶ Start** automatically resumes the playback context.
- Check `echo_target_language` in `liveapiworker.py` (when `False`, speech matching the target language remains silent).
</details>

<details>
<summary><strong>🌐 Language Support</strong></summary>

- Gemini 3.5 Live uses standard BCP-47 language tags (e.g., `zh-Hans` for Simplified Chinese, `zh-Hant` for Traditional Chinese, `en` for English).
- Older non-standard codes such as `cmn-CN` are not supported by Gemini 3.5 Live.
</details>

---

<p align="center">
  Built with ❤️ using <a href="https://cloud.google.com/vertex-ai">Google Vertex AI</a> · <a href="https://fastapi.tiangolo.com/">FastAPI</a>
</p>
