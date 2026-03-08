#!/usr/bin/env python3
"""Unified CLI for openclaw-voice-io.

Commands:
  doctor                Preflight checks (ffmpeg + STT model; optional Feishu sender deps)
  download-models       Download models (STT Sherpa; optional TTS Piper)
  stt                   Voice/audio -> text (prints JSON)
  feishu-send-audio      (Optional) Send Feishu native voice bubble (msg_type=audio)

Examples:
  python scripts/cli.py doctor
  python scripts/cli.py download-models
  python scripts/cli.py stt ~/.openclaw/media/inbound/xxx.ogg

  # Feishu sender (optional)
  python scripts/cli.py feishu-send-audio --receive-id-type open_id --receive-id ou_xxx --text "hello"
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_py(script_path: Path, argv: list[str]) -> int:
    cmd = [sys.executable, str(script_path), *argv]
    return subprocess.call(cmd)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("doctor")
    p.set_defaults(fn=lambda _a: run_py(ROOT / "scripts" / "doctor.py", []))

    p = sub.add_parser("download-models")
    p.add_argument("--models-dir", help="Where to store models (default: ./models)")
    p.add_argument("--stt-only", action="store_true", help="Only download STT (Sherpa) models")
    p.set_defaults(
        fn=lambda a: run_py(
            ROOT / "scripts" / "download_models.py",
            (["--models-dir", a.models_dir] if a.models_dir else [])
            + (["--stt-only"] if a.stt_only else []),
        )
    )

    p = sub.add_parser("stt")
    p.add_argument("audio", help="Audio file path (ogg/opus/m4a/mp3/wav...)")
    p.set_defaults(
        fn=lambda a: run_py(
            ROOT / "skills" / "voice-input-normalizer" / "scripts" / "voice_to_text.py",
            [a.audio],
        )
    )

    p = sub.add_parser("feishu-send-audio")
    p.add_argument("--receive-id-type", required=True, choices=["open_id", "chat_id", "user_id", "union_id"])
    p.add_argument("--receive-id", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--wav")
    p.set_defaults(
        fn=lambda a: run_py(
            ROOT / "adapters" / "feishu" / "scripts" / "feishu_audio_send.py",
            [
                "--receive-id-type",
                a.receive_id_type,
                "--receive-id",
                a.receive_id,
                *( ["--text", a.text] if a.text else ["--wav", a.wav] ),
            ],
        )
    )

    args = ap.parse_args()
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
