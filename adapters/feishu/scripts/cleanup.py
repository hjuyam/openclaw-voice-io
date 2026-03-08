#!/usr/bin/env python3
"""Temp file cleanup helpers for feishu voice MVP.

Policy:
- All temp artifacts live under TMP_DIR.
- On success: delete immediately.
- On failure: keep for FAIL_TTL_SECONDS (default 30 minutes), then purge.

This module is safe: it only ever deletes paths inside TMP_DIR.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

TMP_DIR = Path(os.getenv("FEISHU_VOICE_TMP_DIR", "./tmp/feishu_voice_mvp")).resolve()
FAIL_TTL_SECONDS = int(os.getenv("FEISHU_VOICE_FAIL_TTL_SECONDS", "1800"))


def ensure_tmp_dir() -> Path:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    return TMP_DIR


def safe_unlink(path: Path) -> None:
    """Unlink a file only if it is under TMP_DIR."""
    try:
        rp = path.resolve()
    except Exception:
        return
    if not str(rp).startswith(str(TMP_DIR) + os.sep):
        return
    try:
        if rp.is_file() or rp.is_symlink():
            rp.unlink(missing_ok=True)
    except Exception:
        pass


def purge_expired(now: float | None = None) -> int:
    ensure_tmp_dir()
    now = now or time.time()
    deleted = 0
    for p in TMP_DIR.rglob("*"):
        if not p.is_file():
            continue
        try:
            age = now - p.stat().st_mtime
        except Exception:
            continue
        if age > FAIL_TTL_SECONDS:
            safe_unlink(p)
            deleted += 1
    return deleted


def new_temp_path(stem: str, suffix: str) -> Path:
    ensure_tmp_dir()
    ts = int(time.time() * 1000)
    return TMP_DIR / f"{stem}-{ts}{suffix}"
