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
| 🔀 | **模式选择器** | 支持在**实时同传**（`gemini-3.5-live-translate-preview`）与**实时转录**（`gemini-3.5-transcribe-live-preview`）之间无缝切换 |
| 🎤 | **实时音频流** | MediaStream API + AudioWorklet 采集 16 kHz 单声道 PCM，以 100ms 规整数据包流式传输 |
| 🌍 | **78 种语言** | 完整覆盖 Gemini 3.5 Live 官方语言库，使用标准 BCP-47 代码（如 `zh-Hans` 简体中文、`zh-Hant` 繁体中文、`en` 英语、`ja` 日语等） |
| 🌐 | **多源语言识别** | 支持勾选多个输入语言代码，用于自动语种识别与转录 |
| 🗣️ | **译文语音回放** | 24 kHz 16-bit 线性 PCM 音频流式推回浏览器，使用 Web Audio API 低延迟播放 |
| 🔒 | **智能上下文 UI** | 切换至转录模式时，目标语言选择与语音回放开关自动置灰并禁用 |
| 🎧 | **浏览器级回声消除与降噪** | 启用 `echoCancellation`、`noiseSuppression`、`autoGainControl` 降低回音与环境杂音 |
| 🎭 | **情感化语音** | 启用 `enable_affective_dialog`，合成语音语气贴近说话人情感 |
| ⏱️ | **服务端 VAD** | 针对同传场景调优的自动语音活动检测，极低启动与结束延迟 |
| 🚦 | **不打断进行中的翻译** | `activity_handling = NO_INTERRUPTION`，避免用户停顿或背景杂音截断翻译 |
| 🧠 | **上下文滑动窗口** | 8192 tokens 上下文压缩，保障长时间持续会话不中断 |
| 🔌 | **实时连接状态指示** | 清晰显示 浏览器 ↔ 后端 ↔ Live API 的连接与重连状态 |
| ⏸️ | **停止/开始即时恢复** | 停止仅暂停音频传输并维持后端会话存活，短时间内再次点击「开始」无需重新握手 |
| 🎨 | **零构建原生前端** | 原生 HTML / JavaScript / CSS 开发，无需 Webpack/Vite 打包工具 |

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
   │     └─ 开始/停止/模式/语言切换 → LiveAPIWorker 生命周期管理
   ▼
🤖 LiveAPIWorker (liveapiworker.py) ── Live API 会话管理器 (Vertex AI enterprise=True)
   │
   ├── [模式: 实时同传] ── gemini-3.5-live-translate-preview (源语言识别 + 翻译 + 语音合成)
   └── [模式: 实时转录] ── gemini-3.5-transcribe-live-preview (源语言转录)
   │
   │  WebSocket 回流
   ▼
🌐 浏览器 (index.html)             ── 渲染增量文本 + Web Audio API 播放 24 kHz 合成语音
```

### 详细处理链路

1. **音频采集**：浏览器以 16 kHz 采样率采集单声道音频，开启硬件回声消除、降噪与自动增益。
2. **量化与批处理**：`AudioWorklet`（内建 Blob 容灾降级）将每 100ms（1600 采样点）量化为 16-bit PCM 二进制发送给后端，避免高频请求触发配额限制。
3. **会话建立**：点击「开始」后通过 WebSocket 发送控制消息，`LiveAPIWorker` 与 Google Gemini Live API 建立持久双向流。
4. **Vertex AI 实时推理**：音频流实时发送给部署在 `global` 区域的 Gemini 3.5 模型。
5. **增量结果回推**：后端接收实时转录文本增量（delta）与 24 kHz 语音切片，立即推给浏览器。
6. **渲染与播放**：前端把文本增量拼接为完整对话气泡，并通过 Web Audio 调度音频缓冲无缝播放。

---

## 🏗️ 架构概览

系统采用单一、轻量级全异步 Python 服务架构：

| 层级 | 技术栈 | 关键文件 | 说明 |
|---|---|---|---|
| **前端** | 原生 JS · Web Audio API · AudioWorklet | `static/index.html`、`static/audio-processor.js` | 音频采集、文本增量渲染、24 kHz 语音播放 |
| **后端服务** | Python ≥3.10 · FastAPI · WebSockets | `main.py` | 静态资源托管、WebSocket 通信路由、身份验证 |
| **Live API Worker** | `google-genai` (SDK ≥2.22.0) | `liveapiworker.py` | Vertex AI 双向会话、数据分块、错误重试与保活 |
| **语言代码库** | Python 字典 & BCP-47 规范 | `languages.py` | 78 种 Gemini 3.5 Live 官方标准语言与代码映射 |
| **AI 模型** | Google Vertex AI (`enterprise=True`) | Gemini Live API | `gemini-3.5-live-translate-preview`<br>`gemini-3.5-transcribe-live-preview` |

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
git clone https://github.com/jerryscy/Live-translation-with-Gemini-Live-API-Native-Audio.git
cd Live-translation-with-Gemini-Live-API-Native-Audio

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
DEFAULT_MODE="translation"

# 默认语言 (标准 BCP-47 代码)
DEFAULT_SOURCE_LANG="Chinese (Simplified)"
DEFAULT_SOURCE_LANG_CODE="zh-Hans"
DEFAULT_TARGET_LANG="English"
DEFAULT_TARGET_LANG_CODE="en"

# 会话生命周期
IDLE_CLOSE_SECONDS="30"  # 暂停后保持会话的空闲超时时间（秒）
DEBUG_LIVE_API="false"   # 是否输出底层 Live API 原始调试日志
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

1. **选择功能模式**：
   - **实时同传 (Live Translation)**：将说话内容实时翻译为目标语言，同时输出文本与语音。
   - **实时转录 (Live Transcription)**：仅进行语音转文字，目标语言与语音播放自动置灰关闭。
2. **设置语言**：
   - **输入语言 (Source)**：可勾选一个或多个源语言（例如 `zh-Hans`, `en`）。
   - **目标语言 (Target)**：选择翻译输出的目标语言（仅同传模式下可用）。
3. **开始对话**：
   - 点击 **▶ 开始** 并允许麦克风访问权限。
   - 左侧展示原文识别（type 1），右侧展示译文结果（type 2）。
   - 可随时开关 **播放译文语音** 控制声音播放。
4. **暂停与继续**：
   - 点击 **⏹ 停止** 暂停麦克风采集。
   - 30 秒内再次点击 **▶ 开始**，可秒级无缝恢复录音，无需重新握手连线。

---

## 📦 数据契约

客户端与服务端通过 WebSocket (`ws://127.0.0.1:8000/ws`) 交互：

### 文本消息 (`{"kind": "data", "data": {...}}`)

```json
{
  "uid": "917289fa-4e13-492e-af0c-b33189798dae",
  "seq": 1,
  "type": 2,
  "delta": " The weather is very nice today.",
  "finished": false
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `uid` | string | 浏览器每次连接分配的独立会话标识符 |
| `seq` | integer | 说话轮次序号，每次完整说话结束递增 |
| `type` | integer | `1` = 原文转录，`2` = 译文文本 |
| `delta` | string | 本次收到的增量文本切片 |
| `finished` | boolean | 当前说话轮次是否已结束 |

### 二进制音频消息
- **上行（浏览器 $ightarrow$ 后端）**：16 kHz 16-bit 单声道线性 PCM（约 100ms 切片）。
- **下行（后端 $ightarrow$ 浏览器）**：24 kHz 16-bit 单声道线性 PCM 译文音频。

---

## 🧠 Live API 关键配置

`liveapiworker.py` 针对实时同传和低延迟做了深度参数配置：

| 参数 | 配置值 | 作用说明 |
|---|---|---|
| `client` | `genai.Client(vertexai=True, enterprise=True, location="global")` | 连接 Vertex AI Gemini 3.5 企业级 Live 端点 |
| `response_modalities` | `["AUDIO"]` | 让模型在生成文本转录的同时下发合成语音流 |
| `translation_config` | `target_language`, `echo_target_language=False` | 指定目标语言，当输入已是目标语言时静默不重复播报 |
| `input_audio_transcription` | `AudioTranscriptionConfig()` | 服务端原生语音识别与语种自动判断 |
| `output_audio_transcription` | `AudioTranscriptionConfig()` | 译文语音的同步文本提取 |
| `activity_handling` | `NO_INTERRUPTION` | 防止用户轻微换气或环境杂音切断正在播报的译文 |
| `proactivity` | `proactive_audio=True` | 具备充分上下文时即刻启动流式语音播报 |
| `voice_config` | `prebuilt_voice_config={"voice_name": "puck"}` | 24 kHz 自然拟人音色合成 |

---

## ☁️ Cloud Run 部署

项目中提供了开箱即用的 Cloud Run 部署脚本：

- **无认证公开部署**：
  ```bash
  ./deploy_no_auth.sh
  ```
- **基于 Google OAuth 保护的部署**：
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
