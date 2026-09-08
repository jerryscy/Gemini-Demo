# 🎙️ 实时音频翻译与转录 · Gemini 3.5 Live API

[![zh](https://img.shields.io/badge/lang-中文-red.svg)](./Readme.md)
[![en](https://img.shields.io/badge/lang-English-blue.svg)](./Readme.en.md)

> 基于 Google **Gemini 3.5 Live API**（Vertex AI `google-genai` SDK，`enterprise=True`）的高性能实时语音同传与转录应用。浏览器采集麦克风音频，经 WebSocket 实时传输至后端 → 直接对接 Gemini 3.5 Live 模型（`gemini-3.5-live-translate-preview` 用于同传翻译或 `gemini-3.5-transcribe-live-preview` 用于实时语音转录）→ 同步将**原文转录**、**译文文本**及**合成语音**低延迟推回浏览器即时播放。

---

## 📑 目录

- [✨ 功能亮点](#-功能亮点)
- [🧭 工作流程](#-工作流程)
- [🏗️ 架构概览](#️-架构概览)
- [✅ 先决条件](#-先决条件)
- [⚡ 快速开始](#-快速开始)
- [🔐 配置与身份验证](#-配置与身份验证)
- [🚀 运行与使用](#-运行与使用)
- [📦 数据契约](#-数据契约)
- [🧠 Live API 关键配置](#-live-api-关键配置)
- [☁️ Cloud Run 部署](#️-cloud-run-部署)
- [🛠️ 故障排除](#️-故障排除)

---

## ✨ 功能亮点

| | 功能 | 说明 |
|---|---|---|
| 📝 | **默认实时转录** | 默认启用**实时语音转录**（`gemini-3.5-transcribe-live-preview`），并支持无缝切换至**实时同传**（`gemini-3.5-live-translate-preview`） |
| ⚡ | **开箱自连与免动手推流** | 页面加载完成立即自动连接 WebSocket 及 Gemini Live API，并开启麦克风实时推流 |
| ↻ | **一键重置 (Reset)** | 取代传统开始/停止按钮；点击即可断开已有连接、清屏排空队列、秒启全新 Live 会话并恢复麦克风录音 |
| ⏱️ | **10 分钟会话生命周期保护** | 内建 10 分钟自动倒计时手表；达到 Gemini Live API 单次会话时长硬上限（600 秒）后自动安全终止连接 |
| 📊 | **合并聚合展示面板** | 原文转录与同传译文融合为单一精致卡片：转录模式聚焦展示实时识别内容，同传模式聚焦展示目标译文内容 |
| 🔄 | **切 Tab 自动重连与清屏** | 切换功能选项卡时自动回收旧会话、清空下方旧内容并平滑建立对应模型的新会话 |
| 🎤 | **高保真音频流式传输** | MediaStream API + AudioWorklet 采集 16 kHz 单声道 PCM，以 100ms 规整数据包低延迟流式传输 |
| 🌍 | **78 种语言标准库** | 完整覆盖 Gemini 3.5 Live 官方语言库，使用标准 BCP-47 代码（如 `zh-Hans` 简体中文、`zh-Hant` 繁体中文、`en` 英语、`ja` 日语等） |
| 🌐 | **多源语种自动识别** | 实时转录模式下支持配置多个候选源语种代码，模型自动检测并精准转录 |
| 🗣️ | **译文原生语音合成回放** | 24 kHz 16-bit 线性 PCM 音频流式推回浏览器，使用 Web Audio API 极低延迟平滑播放 |
| 🎧 | **浏览器硬件级降噪** | 启用 `echoCancellation`、`noiseSuppression`、`autoGainControl` 消除回声与背景杂音 |
| 🎭 | **拟人化表达** | 启用 `enable_affective_dialog`，合成语音语调与情感生动贴合说话人语境 |
| 🚦 | **不打断持续播报** | `activity_handling = NO_INTERRUPTION`，避免用户停顿或背景杂音截断翻译 |
| 🧠 | **上下文滑动窗口** | 8192 tokens 上下文压缩，保障会话期间长文本记忆不溢出 |
| 🔌 | **实时连接状态三色灯** | 清晰显示 浏览器 ↔ 后端服务 ↔ Gemini Live API 的实时在线状态 |
| 🚀 | **一键 Cloud Run 部署** | 提供 `deploy.sh`、`deploy_no_auth.sh` 与 `deploy_with_oauth.sh`，无缝交付上云 |

---

## 🧭 工作流程

```
🎙️ 麦克风
   │  16 kHz 单声道 PCM (100ms 分块)
   ▼
🌐 浏览器 (AudioWorklet)          ── 32-bit float → 16-bit PCM
   │                                 麦克风约束：echoCancellation / noiseSuppression / autoGainControl
   │  WebSocket (二进制 PCM 音频 + JSON 控制指令)
   ▼
⚙️  FastAPI 后端 (main.py)         ── 双向异步消息路由器
   │     ├─ 音频流 → LiveAPIWorker.send_audio_data()
   │     └─ 重置 / 模式 / 语言切换 → LiveAPIWorker 生命周期管理
   ▼
🤖 LiveAPIWorker (liveapiworker.py) ── Live API 会话管理器 (Vertex AI enterprise=True)
   │
   ├── [默认模式: 实时转录] ── gemini-3.5-transcribe-live-preview (response_modalities=["TEXT"])
   └── [切换模式: 实时同传] ── gemini-3.5-live-translate-preview (response_modalities=["AUDIO"])
   │
   │  WebSocket 回流
   ▼
🌐 浏览器 (index.html)             ── 实时结果面板增量渲染 + Web Audio API 播放 24 kHz 合成语音
```

### 详细处理链路

1. **自动连线与音频采集**：页面打开时，浏览器自动建立与后端的 WebSocket 连接，并向 Gemini Live API 发起预握手。麦克风自动开启 16 kHz 采样率采集（含回声消除、降噪与自动增益）。
2. **量化与批处理**：`AudioWorklet`（内建 Blob 自动容灾降级）将每 100ms（1600 采样点）量化为 16-bit PCM 二进制包发送给后端。
3. **Vertex AI 实时推理**：音频流实时转发至部署在 `global` 区域的 Gemini 3.5 对应模型。
4. **增量结果回推**：后端接收实时转录文本增量（delta）与 24 kHz 语音切片，即刻推送到浏览器。
5. **渲染与回放**：前端合并面板增量展示转录/翻译气泡，并利用 Web Audio 调度音频缓冲无缝播放译文。
6. **10 分钟周期与一键重置**：10 分钟倒计时归零时自动终止会话；点击「↻ 重置」按钮可瞬时断开旧会话、清屏重置计时器并启动新连接。

---

## 🏗️ 架构概览

系统采用单一、轻量级全异步 Python 服务架构：

| 层级 | 技术栈 | 关键文件 | 说明 |
|---|---|---|---|
| **前端** | 原生 JS · Web Audio API · AudioWorklet | `static/index.html`、`static/audio-processor.js` | 自动推流、文本增量渲染、24 kHz 语音播放、10m 倒计时与重置 |
| **后端服务** | Python ≥3.10 · FastAPI · WebSockets | `main.py` | 静态资源托管、WebSocket 通信路由、OAuth 身份验证支持 |
| **Live API Worker** | `google-genai` (SDK ≥2.22.0) | `liveapiworker.py` | Vertex AI 双向会话、数据分块、10 分钟超时看门狗与重置管理 |
| **语言代码库** | Python 字典 & BCP-47 规范 | `languages.py` | 78 种 Gemini 3.5 Live 官方标准语言与代码映射 |
| **AI 模型** | Google Vertex AI (`enterprise=True`) | Gemini Live API | `gemini-3.5-transcribe-live-preview`<br>`gemini-3.5-live-translate-preview` |

---

## ✅ 先决条件

- **Python 3.10+**（已在 Python 3.10 ~ 3.14 环境测试通过）
- 已安装并完成登录的 **Google Cloud SDK (`gcloud`)**
- 已开启 **Vertex AI API** 的 GCP 项目
- 支持麦克风录音的现代浏览器（推荐 Google Chrome 或 Microsoft Edge）

---

## ⚡ 快速开始

```bash
# 1. 克隆代码仓库
git clone https://github.com/jerryscy/Gemini-Demo.git
cd Gemini-Demo

# 2. 创建虚拟环境并安装依赖
python3 -m venv .venv-app
./.venv-app/bin/pip install --index-url https://pypi.org/simple -r requirements.txt

# 3. 配置环境变量
cp .env.example .env

# 4. 登录 Google Cloud 应用程序默认凭据 (ADC)
gcloud auth application-default login

# 5. 启动应用
./run.sh
```

在浏览器中打开 **`http://127.0.0.1:8000`**。

---

## 🔐 配置与身份验证

### 1. 环境变量配置 (`.env`)

根据您的 GCP 项目信息修改 `.env`：

```env
# Google Cloud / Vertex AI 配置
GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
GOOGLE_CLOUD_LOCATION="global"  # Gemini 3.5 Live 模型仅在 "global" 区域提供

# 模型与默认模式
TRANSLATION_MODEL_ID="gemini-3.5-live-translate-preview"
TRANSCRIPTION_MODEL_ID="gemini-3.5-transcribe-live-preview"
DEFAULT_MODE="transcription"
LIVE_API_MODEL="gemini-3.5-transcribe-live-preview"

# 默认语言 (标准 BCP-47 代码)
DEFAULT_SOURCE_LANG="Chinese (Simplified)"
DEFAULT_SOURCE_LANG_CODE="zh-Hans"
DEFAULT_TARGET_LANG="English"
DEFAULT_TARGET_LANG_CODE="en"

# 会话生命周期
IDLE_CLOSE_SECONDS="600"  # 空闲超时及 10 分钟（600 秒）会话生命周期
DEBUG_LIVE_API="false"    # 是否输出底层 Live API 原始调试日志
```

### 2. 身份验证

本地运行使用 Application Default Credentials (ADC)：

```bash
gcloud auth application-default login
gcloud config set project your-gcp-project-id
```

---

## 🚀 运行与使用

使用启动脚本：
```bash
./run.sh
```

或直接使用 `uvicorn` 启动：
```bash
./.venv-app/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Web 界面操作说明

1. **自动连线与录音**：
   - 网页加载完成后，状态栏中的 **Server** 与 **Live API** 指示灯自动转绿。
   - 页面自动开始采集麦克风音频，右上角倒计时显示 `10:00`。
2. **选择功能模式**：
   - **实时转录 (Live Transcription，默认)**：针对语音做高精度原生转录，下方结果区展示识别文字。
   - **实时同传 (Live Translation)**：将说话内容实时翻译为目标语言，同时输出文本与语音。
   - *切换模式时，系统会自动清空旧内容并重新建立对应模型的专属连接。*
3. **设置语言**：
   - **输入语言 (Source)**：支持配置一个或多个源语言代码（例如 `zh-Hans`, `en`）。
   - **目标语言 (Target)**：选择翻译输出的目标语言（仅同传模式下可用）。
4. **一键重置 (Reset)**：
   - 如需重置会话或清空屏幕，点击顶部的 **`↻ Reset`** 按钮。
   - 系统将断开旧连接、清空界面显示、重置 10 分钟计时并秒级建立全新会话。
5. **10 分钟到期保护**：
   - 达到 10 分钟后，计时器显示 `00:00 (10m Due)`，连接自动安全关闭。点击 **`↻ Reset`** 即可随时开启新的一轮会话。

---

## 📦 数据契约

客户端与服务端通过 WebSocket (`ws://127.0.0.1:8000/ws`) 交互：

### 控制消息（客户端 $\rightarrow$ 服务端）

```json
{"action": "reset"}              // 断开旧连接、清空状态并重新建立 Live API 会话
{"action": "terminate_session"}  // 10 分钟到期后终止当前会话
{"action": "set_mode", "mode": "transcription"} // 切换模式
```

### 文本消息（服务端 $\rightarrow$ 客户端）

```json
{
  "uid": "917289fa-4e13-492e-af0c-b33189798dae",
  "seq": 1,
  "type": 1,
  "delta": " 今天天气非常好。",
  "finished": false
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `uid` | string | 当前会话唯一标识符（Reset 后自动更新） |
| `seq` | integer | 说话轮次序号，每次完整说话结束递增 |
| `type` | integer | `1` = 原文转录，`2` = 译文文本 |
| `delta` | string | 本次收到的增量文本切片 |
| `finished` | boolean | 当前说话轮次是否已结束 |

### 二进制音频消息
- **上行（浏览器 $\rightarrow$ 后端）**：16 kHz 16-bit 单声道线性 PCM（约 100ms 切片）。
- **下行（后端 $\rightarrow$ 浏览器）**：24 kHz 16-bit 单声道线性 PCM 译文音频（仅同传模式输出）。

---

## 🧠 Live API 关键配置

`liveapiworker.py` 根据不同模式精准适配 Gemini 3.5 Live 的配置规范：

### 1. 实时转录 (`gemini-3.5-transcribe-live-preview`)
```python
types.LiveConnectConfig(
    response_modalities=["TEXT"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="puck")
        )
    ),
    input_audio_transcription=types.AudioTranscriptionConfig(
        language_codes=source_language_codes  # 指定一个或多个源语言代码
    ),
    enable_affective_dialog=True,
)
```

### 2. 实时同传 (`gemini-3.5-live-translate-preview`)
```python
types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="puck")
        )
    ),
    input_audio_transcription=types.AudioTranscriptionConfig(), # 不带 language_codes
    output_audio_transcription=types.AudioTranscriptionConfig(
        language_code=target_language_code # 与 translation_config 共享相同目标语言
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

## ☁️ Cloud Run 部署

项目包含生产就绪的部署脚本，完全避免敏感凭证泄漏：

- **通用一键部署**：
  ```bash
  ./deploy.sh
  ```
- **公开访问部署 (无需登录)**：
  ```bash
  ./deploy_no_auth.sh
  ```
- **企业级 Google OAuth 认证保护部署**：
  ```bash
  ./deploy_with_oauth.sh
  ```

---

## 🛠️ 故障排除

<details>
<summary><strong>🔑 身份验证与配额报错</strong></summary>

- 执行 `gcloud auth application-default login` 重新登录凭据。
- 确认 GCP 控制台中该项目已开启 **Vertex AI API**。
- 确认 `.env` 中的 `GOOGLE_CLOUD_LOCATION="global"`（Gemini 3.5 Live 目前仅支持 global 区域）。
</details>

<details>
<summary><strong>🎤 麦克风无法录音或提示 AudioWorklet 错误</strong></summary>

- 在浏览器设置中允许当前网址访问麦克风。
- `AudioWorklet` 要求必须在安全上下文（`https://` 或 `http://localhost` / `http://127.0.0.1`）下运行。
- 代码已集成基于内联 Blob 的自动降级加载，彻底杜绝跨域或 MIME 模块加载失败。
</details>

<details>
<summary><strong>🔇 实时同传没有声音或没有文字输出</strong></summary>

- 确认 UI 顶部的 **播放译文语音** 开关已处于打开状态。
- 浏览器由于 Autoplay 策略，初次加载时可能将 AudioContext 挂起，点击界面的 **▶ 开始** 会自动恢复播放上下文。
- 检查 `liveapiworker.py` 中的 `echo_target_language` 配置（设置为 `False` 时，与目标语言相同的输入将保持静默）。
</details>

<details>
<summary><strong>🌐 语言代码兼容性</strong></summary>

- Gemini 3.5 Live 采用标准 BCP-47 规范语言代码（如简体中文必须为 `zh-Hans`，繁体中文为 `zh-Hant`，英语为 `en`）。
- 旧版的非标准代码（如 `cmn-CN`）已被彻底移除。
</details>

---

<p align="center">
  基于 <a href="https://cloud.google.com/vertex-ai">Google Vertex AI</a> · <a href="https://fastapi.tiangolo.com/">FastAPI</a> 倾情构建
</p>
