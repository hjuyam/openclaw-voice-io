# openclaw-voice-io

A cross-channel voice I/O foundation repo:

- **Voice input (voice → text)**: treat voice as just another form of command input. Do STT normalization once at the very beginning and output text; downstream handling is identical to normal text commands.
- **Voice output (text → Feishu native voice bubble)**: provided as an optional channel adapter (Feishu `msg_type=audio`).

Chinese version: [`README.md`](./README.md)

---

## Ultra-minimal install (ask your OpenClaw)

Copy the text below and send it to your OpenClaw:

> Based on my OS (Windows/macOS/Linux), help me install this skill/repo: https://github.com/hjuyam/openclaw-voice-io/ . Include all required dependencies (Python/ffmpeg/Piper, etc.). Prefer uv; prefer Piper binary and explain how to set PIPER_BIN; do not ask me to paste any secrets (I will fill FEISHU_APP_ID/FEISHU_APP_SECRET myself).

---

## Principles

1) **Voice command == Text command (same level)**
- The only difference is an STT step to produce `normalized_text`
- After that, parsing/execution/feedback is identical to text commands

2) **Cross-channel reuse**
- Core STT is not tied to Feishu/Telegram
- Channel adapters only handle “get audio” / “send message”

3) **Disk-friendly by default**
- Always cleans up normalization temp artifacts
- By default, deletes input audio under OpenClaw inbound dir after successful STT (best-effort)

---

## What you get

### A) Cross-channel: voice → text (core)
- Path: `skills/voice-input-normalizer/`
- Engine: Sherpa-ONNX Paraformer (offline)
- Input: common audio formats (ogg/opus/m4a/mp3/wav...)
- Output: structured JSON (text + metadata)

### B) Optional: Feishu native voice bubble sender (adapter)
- Path: `adapters/feishu/`
- Upload OPUS → `file_key` → send `msg_type=audio`

---

## Quick start

### 0) Install deps

Minimum:
- Python 3.10+
- `ffmpeg`

Recommended with `uv`:

```bash
uv venv
uv pip install -r requirements.txt
```

### 1) Configure env

```bash
cp .env.example .env
```

At least:
- `SHERPA_ONNX_MODEL_DIR`

Optional (for Feishu sender):
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`

### 2) Voice → text

```bash
export SHERPA_ONNX_MODEL_DIR=/path/to/sherpa-model-dir
python skills/voice-input-normalizer/scripts/voice_to_text.py /path/to/audio.ogg
```

### 3) Feishu send voice bubble (optional)

```bash
python adapters/feishu/scripts/feishu_audio_send.py \
  --receive-id-type open_id \
  --receive-id ou_xxx \
  --text "Hello from Feishu audio bubble"

python adapters/feishu/scripts/feishu_audio_send.py \
  --receive-id-type open_id \
  --receive-id ou_xxx \
  --wav /path/to/input.wav
```

---

## Notes

- Never commit `.env`, tokens, models, or generated audio.
- If you only need STT, you can use `skills/voice-input-normalizer/` alone and ignore Feishu/Piper parts.
