#!/usr/bin/env python3
"""Voice/audio → text normalizer (offline STT).

Design:
- Accept common audio formats (wav/opus/m4a/mp3...)
- Normalize to 16k mono WAV (PCM16) with ffmpeg
- Run Sherpa-ONNX offline paraformer recognizer
- Output a JSON dict (stdout) for auditability

Usage:
  python scripts/voice_to_text.py /path/to/audio.opus

Env:
  SHERPA_ONNX_MODEL_DIR (required)
  STT_NUM_THREADS (optional, default 1)

Exit codes:
  0: ok
  2: user/config error
  3: runtime error
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import shutil
import tempfile
import time
import wave
from array import array
from pathlib import Path

import sherpa_onnx


def _build_recognizer(model_dir: Path) -> sherpa_onnx.OfflineRecognizer:
    model = None
    for cand in [
        model_dir / "model.int8.onnx",
        model_dir / "model.onnx",
        model_dir / "model.fp32.onnx",
    ]:
        if cand.exists():
            model = cand
            break
    if model is None:
        raise FileNotFoundError(f"No paraformer model found in {model_dir}")

    tokens = model_dir / "tokens.txt"
    if not tokens.exists():
        raise FileNotFoundError(f"tokens.txt not found in {model_dir}")

    num_threads = int(os.getenv("STT_NUM_THREADS", "1"))

    return sherpa_onnx.OfflineRecognizer.from_paraformer(
        paraformer=str(model),
        tokens=str(tokens),
        num_threads=num_threads,
        sample_rate=16000,
        feature_dim=80,
        decoding_method="greedy_search",
        debug=False,
        provider="cpu",
    )


def _normalize_to_wav_16k_mono(input_path: Path) -> tuple[Path, Path]:
    """Return (normalized_wav, tmpdir). Caller is responsible for cleanup."""
    tmpdir = Path(tempfile.mkdtemp(prefix="voice_norm_"))
    out_wav = tmpdir / "normalized.wav"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        str(out_wav),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return out_wav, tmpdir


def _wav_duration_ms(wav_path: Path) -> int:
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        sr = wf.getframerate()
    if sr <= 0:
        return 0
    return int(frames * 1000 / sr)


def transcribe_file(path: str) -> dict:
    t0 = time.time()
    input_path = Path(path).expanduser().resolve()
    if not input_path.exists():
        return {
            "ok": False,
            "error": f"file not found: {input_path}",
            "input_path": str(input_path),
        }

    model_dir = os.getenv("SHERPA_ONNX_MODEL_DIR")
    if not model_dir:
        return {"ok": False, "error": "SHERPA_ONNX_MODEL_DIR is not set"}

    model_dir_path = Path(model_dir).expanduser().resolve()
    if not model_dir_path.exists():
        return {"ok": False, "error": f"model dir not found: {model_dir_path}"}

    normalized_wav, tmpdir = _normalize_to_wav_16k_mono(input_path)

    try:
        recognizer = _build_recognizer(model_dir_path)
        stream = recognizer.create_stream()

        with wave.open(str(normalized_wav), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            samples_i16 = array("h")
            samples_i16.frombytes(frames)

        samples = [s / 32768.0 for s in samples_i16]
        stream.accept_waveform(16000, samples)

        recognizer.decode_stream(stream)
        result = stream.result
        text = (result.text or "").strip()

        # Optional: delete inbound input audio after successful STT to reduce disk.
        delete_input = os.getenv("STT_DELETE_INPUT_ON_SUCCESS", "1") == "1"
        inbound_prefix = os.getenv("OPENCLAW_INBOUND_DIR", "/root/.openclaw/media/inbound")
        input_deleted = False
        if delete_input:
            try:
                inb = Path(inbound_prefix).expanduser().resolve()
                if inb in input_path.parents:
                    input_path.unlink(missing_ok=True)
                    input_deleted = True
            except Exception:
                # best-effort: never fail STT result because cleanup failed
                input_deleted = False

        return {
            "ok": True,
            "text": text,
            "engine": "sherpa-onnx-paraformer",
            "model_dir": str(model_dir_path),
            "input_path": str(input_path),
            "normalized_wav": str(normalized_wav),
            "duration_ms": _wav_duration_ms(normalized_wav),
            "elapsed_ms": int((time.time() - t0) * 1000),
            "input_deleted": input_deleted,
        }
    finally:
        # Always cleanup normalization temp dir.
        shutil.rmtree(tmpdir, ignore_errors=True)


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print(__doc__.strip())
        return 0

    try:
        res = transcribe_file(sys.argv[1])
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res.get("ok") else 2
    except subprocess.CalledProcessError as e:
        print(json.dumps({"ok": False, "error": f"ffmpeg failed: {e}"}, ensure_ascii=False))
        return 3
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
