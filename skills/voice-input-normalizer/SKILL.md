# voice-input-normalizer (O8)

**Goal**: Treat *voice input* as just another command input form.

This skill **normalizes voice/audio → text** at the very beginning of the pipeline, so that:

- Voice command == Text command (same downstream parsing/execution)
- The *only* difference is an extra STT step

## What this skill provides

- Offline speech-to-text (STT) via **Sherpa-ONNX Paraformer**
- Input audio normalization via **ffmpeg** (any common formats → 16k mono WAV)
- A stable CLI + Python module API
- Structured JSON output (text + metadata) suitable for logging / indexing / audit

## Non-goals

- No TTS
- No “send audio bubble” (channel-specific outbound)

## Requirements

- Python 3.10+
- `ffmpeg`
- Python deps: see `requirements.txt`

## Environment variables

- `SHERPA_ONNX_MODEL_DIR` (required)
  - Must contain `tokens.txt` and one of: `model.int8.onnx` / `model.onnx` / `model.fp32.onnx`
- Optional:
  - `STT_NUM_THREADS` (default 1)
  - `STT_DELETE_INPUT_ON_SUCCESS=1` (default 1)
    - If enabled, delete the *input audio file* after successful STT **only when** it is under `OPENCLAW_INBOUND_DIR`.
  - `OPENCLAW_INBOUND_DIR` (default `/root/.openclaw/media/inbound`)

## Install (suggested)

```bash
cd /root/.openclaw/workspace/skills/voice-input-normalizer
uv venv
uv pip install -r requirements.txt
```

(If you don’t use uv, use `python -m venv .venv` + pip.)

## Download model

This skill does not auto-download models.

You can reuse an existing Sherpa model directory (recommended) or download one manually.

Recommended model (zh small paraformer):
- https://github.com/k2-fsa/sherpa-onnx/releases

## Usage

### CLI (prints JSON)

```bash
export SHERPA_ONNX_MODEL_DIR=/root/.openclaw/workspace/tools/voice_mvp/models/sherpa/sherpa-onnx-paraformer-zh-small-2024-03-09
python scripts/voice_to_text.py /path/to/audio.opus
```

Output example:

```json
{
  "ok": true,
  "text": "...",
  "engine": "sherpa-onnx-paraformer",
  "model_dir": "...",
  "input_path": "...",
  "normalized_wav": "...",
  "duration_ms": 1234
}
```

### Python API

```python
from scripts.voice_to_text import transcribe_file
res = transcribe_file("/path/to/audio.opus")
print(res["text"])
```

## Integration guideline (cross-channel)

Channel adapters (Feishu/Telegram/others) should only do:

1) Obtain audio bytes/file and save to disk
2) Call this skill to get `normalized_text`
3) Feed `normalized_text` into the existing text-command pipeline
4) Store (audio reference + text + metadata) for audit/search

If recognition is empty/low-confidence, do **clarification** instead of executing.
