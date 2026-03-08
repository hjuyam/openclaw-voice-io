#!/usr/bin/env python3
"""Cross-platform model downloader for this project.

Downloads:
- Sherpa-ONNX offline ASR (paraformer zh-small)
- Piper voice model (zh_CN huayan x_low)

This script is intentionally pure-Python (no bash, no curl) for Windows/macOS/Linux.

Usage:
  python scripts/download_models.py
  python scripts/download_models.py --models-dir ./models

Env:
  MODELS_DIR can override default as well.

Notes:
- We do NOT commit models to git. This downloads them locally.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path


SHERPA_TARBZ2_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "sherpa-onnx-paraformer-zh-small-2024-03-09.tar.bz2"
)
SHERPA_DIRNAME = "sherpa-onnx-paraformer-zh-small-2024-03-09"

PIPER_ONNX_URL = "https://huggingface.co/csukuangfj/vits-piper-zh_CN-huayan-x_low/resolve/main/zh_CN-huayan-x_low.onnx"
PIPER_JSON_URL = "https://huggingface.co/csukuangfj/vits-piper-zh_CN-huayan-x_low/resolve/main/zh_CN-huayan-x_low.onnx.json"
PIPER_ONNX_NAME = "zh_CN-huayan-x_low.onnx"
PIPER_JSON_NAME = "zh_CN-huayan-x_low.onnx.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".partial")
    if tmp.exists():
        tmp.unlink()
    print(f"==> Download: {url}")
    with urllib.request.urlopen(url) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    tmp.replace(out)


def ensure_sherpa(models_dir: Path) -> None:
    sherpa_root = models_dir / "sherpa"
    target_dir = sherpa_root / SHERPA_DIRNAME
    if target_dir.exists():
        print(f"==> Sherpa model exists: {target_dir}")
        return

    sherpa_root.mkdir(parents=True, exist_ok=True)
    tar_path = sherpa_root / (SHERPA_DIRNAME + ".tar.bz2")
    download(SHERPA_TARBZ2_URL, tar_path)

    print(f"==> Extract: {tar_path}")
    with tarfile.open(tar_path, "r:bz2") as tf:
        tf.extractall(path=sherpa_root)

    tar_path.unlink(missing_ok=True)
    if not target_dir.exists():
        raise RuntimeError(f"Extracted but missing directory: {target_dir}")

    print(f"==> Sherpa ready: {target_dir}")


def ensure_piper(models_dir: Path) -> None:
    piper_root = models_dir / "piper"
    piper_root.mkdir(parents=True, exist_ok=True)

    onnx_path = piper_root / PIPER_ONNX_NAME
    json_path = piper_root / PIPER_JSON_NAME

    if not onnx_path.exists():
        download(PIPER_ONNX_URL, onnx_path)
        print(f"    sha256({onnx_path.name})={sha256_file(onnx_path)}")
    else:
        print(f"==> Piper voice exists: {onnx_path}")

    if not json_path.exists():
        download(PIPER_JSON_URL, json_path)
        print(f"    sha256({json_path.name})={sha256_file(json_path)}")
    else:
        print(f"==> Piper config exists: {json_path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--models-dir",
        default=os.getenv("MODELS_DIR", "./models"),
        help="Where to store downloaded models (default: ./models)",
    )
    args = ap.parse_args()

    models_dir = Path(args.models_dir).expanduser().resolve()
    models_dir.mkdir(parents=True, exist_ok=True)

    ensure_sherpa(models_dir)
    ensure_piper(models_dir)

    print("\nAll done.")
    print(f"Models directory: {models_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
