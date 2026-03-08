#!/usr/bin/env python3
"""Send a Feishu *audio* message (voice bubble) using Feishu OpenAPI.

Chain:
  text -> Piper wav -> ffmpeg opus -> Feishu upload(file_type=opus, duration ms) -> msg_type=audio

Env:
  FEISHU_APP_ID / FEISHU_APP_SECRET
  FEISHU_DOMAIN (optional, default https://open.feishu.cn)
  PIPER_VOICE / PIPER_VOICE_CONFIG (required when using --text)

Usage:
  python3 scripts/feishu_audio_send.py --receive-id-type open_id --receive-id ou_xxx --text "hello"

Notes:
- DM: receive_id_type=open_id, receive_id=ou_xxx
- Group: receive_id_type=chat_id, receive_id=oc_xxx
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import wave
from pathlib import Path

import requests

from cleanup import new_temp_path, purge_expired, safe_unlink


def feishu_base() -> str:
    dom = os.getenv("FEISHU_DOMAIN", "https://open.feishu.cn").rstrip("/")
    return dom


def get_tenant_access_token() -> str:
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise RuntimeError("FEISHU_APP_ID/FEISHU_APP_SECRET not set")

    url = f"{feishu_base()}/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": app_id, "app_secret": app_secret}, timeout=20)
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"token error: {data}")
    return data["tenant_access_token"]


def wav_duration_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
    return int(frames / rate * 1000)


def add_leading_silence(wav_path: Path, silence_ms: int) -> Path:
    """Create a new wav with leading silence (best-effort).

    This improves the UX for some clients that may clip the beginning.
    """
    if silence_ms <= 0:
        return wav_path

    out_wav = new_temp_path("tts-pad", ".wav")
    silence_sec = silence_ms / 1000.0

    # Prepend silence: anullsrc (mono/16k) + input wav -> concat
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-t",
        f"{silence_sec}",
        "-i",
        "anullsrc=r=16000:cl=mono",
        "-i",
        str(wav_path),
        "-filter_complex",
        "[0:a][1:a]concat=n=2:v=0:a=1",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(out_wav),
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return out_wav


def to_opus(wav_path: Path) -> Path:
    opus_path = new_temp_path("tts", ".opus")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(wav_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "libopus",
        "-b:a",
        "24k",
        str(opus_path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return opus_path


def upload_opus(token: str, opus_path: Path, duration_ms: int) -> str:
    url = f"{feishu_base()}/open-apis/im/v1/files"
    headers = {"Authorization": f"Bearer {token}"}

    with open(opus_path, "rb") as f:
        files = {"file": ("voice.opus", f, "audio/opus")}
        data = {
            "file_type": "opus",
            "duration": str(duration_ms),
        }
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)

    j = resp.json()
    if j.get("code") != 0:
        raise RuntimeError(f"upload error: {j}")
    return j["data"]["file_key"]


def send_audio_message(token: str, receive_id_type: str, receive_id: str, file_key: str) -> dict:
    url = f"{feishu_base()}/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "receive_id": receive_id,
        "msg_type": "audio",
        "content": json.dumps({"file_key": file_key}, ensure_ascii=False),
    }
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    return resp.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receive-id-type", required=True, choices=["open_id", "chat_id", "user_id", "union_id"])
    ap.add_argument("--receive-id", required=True)

    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--wav", help="Path to wav file to send")

    args = ap.parse_args()

    purge_expired()

    wav_path = None
    padded_wav_path = None
    opus_path = None

    try:
        if args.wav:
            wav_path = Path(args.wav).expanduser().resolve()
        else:
            wav_path = new_temp_path("tts", ".wav")
            cmd = [sys.executable, str(Path(__file__).parent / "piper_tts.py"), args.text, str(wav_path)]
            subprocess.run(cmd, check=True)

        # Optional leading silence for better playback UX
        silence_ms = int(os.getenv("FEISHU_VOICE_LEADING_SILENCE_MS", "800"))
        padded_wav_path = add_leading_silence(wav_path, silence_ms)

        dur = wav_duration_ms(padded_wav_path)
        opus_path = to_opus(padded_wav_path)

        token = get_tenant_access_token()
        file_key = upload_opus(token, opus_path, dur)
        res = send_audio_message(token, args.receive_id_type, args.receive_id, file_key)

        if res.get("code") != 0:
            raise RuntimeError(f"send error: {res}")

        print(json.dumps({"ok": True, "file_key": file_key, "send": res}, ensure_ascii=False))
        return 0

    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1

    finally:
        # delete temp artifacts on success path (best-effort)
        if wav_path is not None:
            safe_unlink(wav_path)
        if padded_wav_path is not None and padded_wav_path != wav_path:
            safe_unlink(padded_wav_path)
        if opus_path is not None:
            safe_unlink(opus_path)


if __name__ == "__main__":
    raise SystemExit(main())
