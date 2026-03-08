# openclaw-voice-io

一个“跨渠道”的语音 I/O 基础能力仓库：

- **语音输入（voice → text）**：把语音当作“文本指令的输入形态”，在入口做一次 STT 归一化，输出文本，后续与普通文本指令同构。
- **语音输出（text → Feishu 原生语音气泡）**：作为可选的渠道适配器（Feishu `msg_type=audio`），不影响核心能力。

> 默认 README 为中文；English version: [`README.en.md`](./README.en.md)

---

## 最简安装（交给你的 OpenClaw）

复制以下内容，发给你的 OpenClaw：

> 根据我的操作系统实际情况，安装 https://github.com/hjuyam/openclaw-voice-io/ 这个 skill（或仓库）。包括必要的依赖（Python/ffmpeg/Piper 等），优先使用 uv；Piper 优先二进制并说明如何配置 PIPER_BIN；不要让我粘贴任何 secret（我会自己填写 FEISHU_APP_ID/FEISHU_APP_SECRET）。

---

## 设计原则

1) **语音指令 = 文本指令（同级）**
- 唯一差别：语音需要先 STT 得到 `normalized_text`
- 后续解析/执行/回执流程与文本完全一致

2) **跨渠道复用**
- 核心 STT 不绑定 Feishu/Telegram
- 渠道适配器只做“拿音频/发消息”的薄封装

3) **磁盘友好（默认清理）**
- STT 归一化产生的临时文件必清理
- 默认开启：识别成功后删除 OpenClaw inbound 目录下的输入音频（best-effort）

---

## 你得到什么

### A) 跨渠道：语音 → 文本（核心）
- 目录：`skills/voice-input-normalizer/`
- 引擎：Sherpa-ONNX Paraformer（离线）
- 输入：常见音频格式（ogg/opus/m4a/mp3/wav...）
- 输出：结构化 JSON（包含 text + 元信息）

### B) 可选：Feishu 发送原生语音气泡（适配器）
- 目录：`adapters/feishu/`
- 通过 Feishu OpenAPI 上传 OPUS → `file_key` → 发送 `msg_type=audio`

---

## 快速开始

### 0) 安装依赖

你至少需要：
- Python 3.10+
- `ffmpeg`

推荐用 `uv`：

```bash
uv venv
uv pip install -r requirements.txt
```

### 1) 配置环境变量

```bash
cp .env.example .env
```

### 2) doctor 自检

```bash
python scripts/cli.py doctor
```

### 3) 下载模型（推荐）

```bash
python scripts/cli.py download-models
# 如果你只需要 STT：
python scripts/cli.py download-models --stt-only
```

### 4) 语音 → 文本（跨渠道）

```bash
export SHERPA_ONNX_MODEL_DIR=./models/sherpa/sherpa-onnx-paraformer-zh-small-2024-03-09
python scripts/cli.py stt /path/to/audio.ogg
```

### 5) Feishu 发送语音气泡（可选）

> 这是渠道适配器，用不用它不影响“语音输入归一化”能力。

```bash
# 文字 -> TTS -> Feishu 语音气泡
python scripts/cli.py feishu-send-audio \
  --receive-id-type open_id \
  --receive-id ou_xxx \
  --text "你好，这是飞书原生语音条。"

# 或者直接发 wav（跳过 TTS）
python scripts/cli.py feishu-send-audio \
  --receive-id-type open_id \
  --receive-id ou_xxx \
  --wav /path/to/input.wav
```

---

## 目录结构

- `skills/voice-input-normalizer/`：跨渠道 STT 归一化（核心）
- `adapters/feishu/`：Feishu 渠道适配器（发送原生语音气泡）
- `.env.example`：参考配置（不提交 `.env`）

---

## 注意

- 不要提交 `.env`、token、模型文件、生成的音频。
- 如果你只需要“语音→文本”，可以只使用 `skills/voice-input-normalizer/`，无需安装/配置 Feishu 或 Piper。
