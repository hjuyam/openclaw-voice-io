#!/usr/bin/env python3
"""Generate WAV using Piper (offline TTS).

Env:
  PIPER_VOICE: path to .onnx
  PIPER_VOICE_CONFIG: path to .onnx.json

Usage:
  python3 scripts/piper_tts.py "text" ./tmp/out.wav
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from cleanup import purge_expired


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] in {"-h", "--help"}:
        print(__doc__.strip())
        return 0

    text = sys.argv[1]
    out_wav = Path(sys.argv[2]).expanduser().resolve()
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    voice = os.getenv("PIPER_VOICE")
    voice_cfg = os.getenv("PIPER_VOICE_CONFIG")
    if not voice or not voice_cfg:
        print("ERROR: PIPER_VOICE and/or PIPER_VOICE_CONFIG not set", file=sys.stderr)
        return 2

    purge_expired()

    piper_bin = os.getenv("PIPER_BIN", "piper")

    cmd = [
        piper_bin,
        "--model",
        voice,
        "--config",
        voice_cfg,
        "--output_file",
        str(out_wav),
    ]

    subprocess.run(cmd, input=text.encode("utf-8"), check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
