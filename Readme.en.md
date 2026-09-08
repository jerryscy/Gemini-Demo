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
| 📝 | **Default Live Transcription** | Launches in **Live Transcription** (`gemini-3.5-transcribe-live-preview`) by default, with seamless one-click switching to **Live Translation** (`gemini-3.5-live-translate-preview`) |
| ⚡ | **Auto-Connect on Page Load** | Automatically connects WebSocket and initializes the Gemini Live API session and mic streaming on page load |
| ↻ | **One-Click Reset** | Replaces Start/Stop toggles; clicking **Reset** disconnects the current session, flushes queues, clears content, and starts a fresh connection instantly |
| ⏱️ | **10-Minute Session Lifecycle** | Visual 10-minute session countdown timer; automatically and cleanly terminates when the Gemini Live API 10-minute maximum limit is reached |
| 📊 | **Consolidated Result Card** | Single unified result view: shows input transcription in Transcription mode, and translated output in Translation mode |
| 🔄 | **Tab-Switch Auto-Reconnection** | Switching tabs automatically cleans up old state, clears previous logs, and establishes the correct Live model session |
| 🎤 | **High-Fidelity Audio Streaming** | MediaStream API + AudioWorklet captures mic audio at 16 kHz mono PCM in regular 100ms packets |
| 🌍 | **78 Languages** | Full Gemini 3.5 Live language catalog using standard BCP-47 codes (e.g., `zh-Hans`, `zh-Hant`, `en`, `es`, `ja`) |
| 🌐 | **Multi-Language Input Detection** | Select one or multiple source languages for speech recognition and language identification |
| 🗣️ | **Translated Speech Playback** | 24 kHz 16-bit linear PCM audio streamed to the browser with Web Audio API playback |
| 🎧 | **Browser Echo/Noise Suppression** | Built-in browser `echoCancellation`, `noiseSuppression`, and `autoGainControl` minimize feedback and distortion |
| 🎭 | **Affective Dialog & Voice Options** | Synthesized translations mirror speaker emotion via `enable_affective_dialog` |
| 🚦 | **No Mid-Turn Interruption** | `activity_handling = NO_INTERRUPTION` prevents background audio from truncating in-progress translations |
| 🧠 | **Context Window Compression** | Sliding token window prevents session drops during extended conversations |
| 🔌 | **Live Connection Indicator** | Real-time status indicators showing Browser ↔ Backend ↔ Live API states |
| 🚀 | **Production-Ready Deploy Scripts** | Pre-built scripts (`deploy.sh`, `deploy_no_auth.sh`, `deploy_with_oauth.sh`) for Google Cloud Run deployment |

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
   │     └─ reset / mode / language controls → LiveAPIWorker lifecycle
   ▼
🤖 LiveAPIWorker (liveapiworker.py) ── Live API session manager (Vertex AI enterprise=True)
   │
   ├── [Default Mode: Transcription] ── gemini-3.5-transcribe-live-preview (response_modalities=["TEXT"])
   └── [Switched Mode: Translation]   ── gemini-3.5-live-translate-preview (response_modalities=["AUDIO"])
   │
   │  WebSocket return stream
   ▼
🌐 Browser (index.html)             ── Consolidated result view rendering + Web Audio API 24 kHz playback
```

### Step-by-Step Flow

1. **Auto-Connect & Capture**: On page load, the browser immediately establishes WebSocket and Live API connections, opening the microphone at 16 kHz mono with hardware echo cancellation, noise suppression, and auto gain control.
2. **Chunking & Quantization**: `AudioWorklet` (with inline Blob fallback) buffers 100ms of audio (1,600 samples) and converts 32-bit float samples to 16-bit linear PCM.
3. **Vertex AI Processing**: Audio is streamed in real time to the selected Gemini 3.5 model in the `global` region.
4. **Streamed Return**: The backend receives translated audio and synchronized transcription deltas, forwarding them immediately to the browser.
5. **Playback & Rendering**: The frontend accumulates text deltas into chat bubbles and decodes/schedules 24 kHz audio buffers for seamless audio playback.
6. **10-Minute Expiry & Reset**: A 10-minute countdown terminates the session when due. Clicking **`↻ Reset`** disconnects the session, clears past text, resets the timer to `10:00`, and starts a fresh connection.

---

## 🏗️ Architecture

The application runs as a lightweight, single-process service:

| Component | Technology | Key Files | Description |
|---|---|---|---|
| **Frontend** | Vanilla JS · Web Audio API · AudioWorklet | `static/index.html`, `static/audio-processor.js` | Auto-capture, delta assembly, 24 kHz playback, 10m timer & Reset |
| **Backend Router** | Python ≥3.10 · FastAPI · WebSockets | `main.py` | HTTP static file serving, WebSocket endpoint, OAuth auth support |
| **Live Worker** | `google-genai` (SDK ≥2.22.0) | `liveapiworker.py` | Vertex AI Live API connection, 10-minute session watchdog & reset logic |
| **Language Metadata** | Python dictionary & BCP-47 codes | `languages.py` | 78 supported Gemini 3.5 Live languages |
| **AI Models** | Vertex AI (`enterprise=True`) | Google Gemini Live API | `gemini-3.5-transcribe-live-preview`<br>`gemini-3.5-live-translate-preview` |

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
git clone https://github.com/jerryscy/Gemini-Demo.git
cd Gemini-Demo

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
DEFAULT_MODE="transcription"
LIVE_API_MODEL="gemini-3.5-transcribe-live-preview"

# Default Languages (BCP-47)
DEFAULT_SOURCE_LANG="Chinese (Simplified)"
DEFAULT_SOURCE_LANG_CODE="zh-Hans"
DEFAULT_TARGET_LANG="English"
DEFAULT_TARGET_LANG_CODE="en"

# Session Lifecycle
IDLE_CLOSE_SECONDS="600"  # Keep-alive window and 10-minute (600s) session cap
DEBUG_LIVE_API="false"    # Set to true for verbose Live API timing logs
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

1. **Auto-Connect**:
   - On page load, the **Server** and **Live API** indicators turn green automatically.
   - Microphone capture begins, and the session timer counts down from `10:00`.
2. **Select Mode**:
   - **Live Transcription (Default)**: High-accuracy speech-to-text. The result card displays input transcriptions.
   - **Live Translation**: Speaks and translates input into the target language.
   - *Changing tabs automatically reconnects and clears previous logs.*
3. **Configure Languages**:
   - **Input Language**: Select one or more source languages (e.g. `zh-Hans`, `en`).
   - **Target Language**: Select output language (active in Translation mode).
4. **One-Click Reset**:
   - Click **`↻ Reset`** at any time to disconnect the current session, clear content, reset the 10-minute timer, and reconnect immediately.
5. **10-Minute Expiry**:
   - When the 10-minute window expires, the timer shows `00:00 (10m Due)` and the connection closes gracefully. Click **`↻ Reset`** to start a new session.

---

## 📦 Data Contract

Client and server communicate via WebSocket (`ws://127.0.0.1:8000/ws`):

### Control Messages (Client $\rightarrow$ Server)

```json
{"action": "reset"}              // Disconnects existing session and connects fresh
{"action": "terminate_session"}  // Cleanly terminates session on 10m expiry
{"action": "set_mode", "mode": "transcription"} // Changes mode and reconnects
```

### Text Messages (Server $\rightarrow$ Client)

```json
{
  "uid": "917289fa-4e13-492e-af0c-b33189798dae",
  "seq": 1,
  "type": 1,
  "delta": " The weather is very nice today.",
  "finished": false
}
```

| Field | Type | Description |
|---|---|---|
| `uid` | string | Unique session identifier (refreshed on Reset) |
| `seq` | integer | Turn counter, increments after each utterance |
| `type` | integer | `1` = Source transcription, `2` = Translated text |
| `delta` | string | Incremental text delta |
| `finished` | boolean | Indicates whether the current turn is complete |

### Binary Audio Messages
- **Upstream (Browser $\rightarrow$ Backend)**: 16 kHz 16-bit mono linear PCM (~100ms packets).
- **Downstream (Backend $\rightarrow$ Browser)**: 24 kHz 16-bit mono linear PCM translated audio (Translation mode only).

---

## 🧠 Live API Model Configuration

`liveapiworker.py` strictly aligns with the Gemini 3.5 Live API protocol:

### 1. Live Transcription (`gemini-3.5-transcribe-live-preview`)
```python
types.LiveConnectConfig(
    response_modalities=["TEXT"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="puck")
        )
    ),
    input_audio_transcription=types.AudioTranscriptionConfig(
        language_codes=source_language_codes  # Source language codes array
    ),
    enable_affective_dialog=True,
)
```

### 2. Live Translation (`gemini-3.5-live-translate-preview`)
```python
types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="puck")
        )
    ),
    input_audio_transcription=types.AudioTranscriptionConfig(), # Without language_codes
    output_audio_transcription=types.AudioTranscriptionConfig(
        language_code=target_language_code # Shared with translation_config
    ),
    translation_config=types.LiveClientTranslationConfig(
        target_language_code=target_language_code,
        echo_target_language=True,
    ),
    activity_handling=types.ActivityHandling.NO_INTERRUPTION,
    proactivity=types.ProactivityConfig(proactive_audio=True),
    enable_affective_dialog=True,
)
```

---

## ☁️ Cloud Run Deployment

Scripts without hardcoded secrets are included for deployment:

- **Unified Deployment Script**:
  ```bash
  ./deploy.sh
  ```
- **Public Service (No Authentication)**:
  ```bash
  ./deploy_no_auth.sh
  ```
- **Secured with Google OAuth**:
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
