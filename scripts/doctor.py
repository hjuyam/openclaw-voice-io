#!/usr/bin/env python3
"""Doctor: preflight checks + install hints.

Checks:
- Python version
- ffmpeg presence
- STT model dir presence (SHERPA_ONNX_MODEL_DIR)

Optional checks (only if you want Feishu sender):
- piper binary presence (PIPER_BIN or `piper` in PATH)
- FEISHU_APP_ID/FEISHU_APP_SECRET presence

Usage:
  python scripts/doctor.py
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def run_version(cmd: list[str]) -> tuple[bool, str]:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return True, out.strip().splitlines()[0][:200]
    except Exception as e:
        return False, str(e)


def hint_ffmpeg() -> str:
    sysname = platform.system().lower()
    if sysname == "darwin":
        return "Install ffmpeg: brew install ffmpeg"
    if sysname == "windows":
        return "Install ffmpeg: winget install Gyan.FFmpeg (or choco install ffmpeg)"
    return "Install ffmpeg: sudo apt-get install ffmpeg (or your distro package manager)"


def hint_uv() -> str:
    sysname = platform.system().lower()
    if sysname == "windows":
        return "Install uv: https://docs.astral.sh/uv/getting-started/installation/ (PowerShell installer)"
    return "Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"


def hint_piper() -> str:
    return (
        "Install Piper (binary preferred):\n"
        "- https://github.com/rhasspy/piper/releases\n"
        "Then set PIPER_BIN to the piper executable path, or ensure `piper` is in PATH.\n"
        "(Fallback: pip install piper-tts)"
    )


def check_sherpa_model_dir() -> tuple[bool, str]:
    model_dir = os.getenv("SHERPA_ONNX_MODEL_DIR")
    if not model_dir:
        return False, "SHERPA_ONNX_MODEL_DIR is not set"

    p = Path(model_dir).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        return False, f"model dir not found: {p}"

    has_tokens = (p / "tokens.txt").exists()
    has_model = any((p / n).exists() for n in ["model.int8.onnx", "model.onnx", "model.fp32.onnx"])
    if not has_tokens or not has_model:
        return False, f"model dir looks incomplete: {p} (need tokens.txt + model*.onnx)"

    return True, f"sherpa model dir ok: {p}"


def main() -> int:
    ok_all = True

    print("== System")
    print(f"platform: {platform.platform()}")
    print(f"python: {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        ok_all = False
        print("[FAIL] Python >= 3.10 required")

    print("\n== Dependency: uv (recommended)")
    uv = which("uv")
    if uv:
        ok, ver = run_version([uv, "--version"])
        print(f"[OK] uv: {ver}")
    else:
        print("[WARN] uv not found")
        print("       " + hint_uv())

    print("\n== Dependency: ffmpeg")
    ff = which("ffmpeg")
    if ff:
        ok, ver = run_version([ff, "-version"])
        print(f"[OK] ffmpeg: {ver}")
    else:
        ok_all = False
        print("[FAIL] ffmpeg not found")
        print("       " + hint_ffmpeg())

    print("\n== STT model")
    ok, msg = check_sherpa_model_dir()
    if ok:
        print(f"[OK] {msg}")
    else:
        ok_all = False
        print(f"[FAIL] {msg}")

    print("\n== Optional: Feishu sender")
    piper_bin = os.getenv("PIPER_BIN") or which("piper")
    if piper_bin:
        ok, _ver = run_version([piper_bin, "--help"])
        print(f"[OK] piper runnable: {piper_bin}" if ok else f"[WARN] piper exists but not runnable: {piper_bin}")
    else:
        print("[INFO] piper not found (ok if you only need STT)")
        print("       " + hint_piper())

    def present(name: str) -> str:
        return "set" if os.getenv(name) else "missing"

    print(f"FEISHU_APP_ID: {present('FEISHU_APP_ID')}")
    print(f"FEISHU_APP_SECRET: {present('FEISHU_APP_SECRET')}")

    print("\n== Result")
    if ok_all:
        print("OK")
        return 0
    print("NOT_OK")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
