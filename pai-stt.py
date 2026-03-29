#!/usr/bin/env python3
"""
PAI STT — push-to-talk na Macu, wkleja transkrypcję do aktywnego okna.
Używa ElevenLabs Scribe v2 Realtime (WebSocket) dla minimalnej latencji.

Mikrofon otwierany tylko na czas nagrywania — pomarańczowa kropka macOS
pojawia się wyłącznie gdy trzymasz hotkey.

Uprawnienia macOS:
    System Settings → Privacy & Security → Accessibility → dodaj swój terminal lub Python

Konfiguracja:
    export ELEVENLABS_API_KEY=your_key

Użycie:
    python3 pai-stt.py &
    Trzymaj ctrl+shift → mów → puść → tekst pojawia się w aktywnym oknie
"""

import base64
import json
import os
import subprocess
import sys
import threading

import numpy as np
import sounddevice as sd
import websockets.sync.client as ws_client
from pynput import keyboard
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
SAMPLE_RATE = 16000
CHANNELS = 1
WS_URL = (
    f"wss://api.elevenlabs.io/v1/speech-to-text/realtime"
    f"?model_id=scribe_v2_realtime"
    f"&audio_format=pcm_16000"
    f"&language_code=pl"
    f"&commit_strategy=manual"
)

_recording = False
_ws = None
_stream = None
_ws_lock = threading.Lock()
_lock = threading.Lock()

_CTRL = {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}
_SHIFT = {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r}
_held: set = set()


# ── websocket ────────────────────────────────────────────────────────────────

def _connect() -> ws_client.ClientConnection:
    return ws_client.connect(
        WS_URL,
        additional_headers={"xi-api-key": API_KEY},
    )


def _send_chunk(audio_f32: np.ndarray, commit: bool = False) -> None:
    with _ws_lock:
        if _ws is None:
            return
        pcm = np.clip(audio_f32 * 32767, -32768, 32767).astype(np.int16)
        msg = {
            "message_type": "input_audio_chunk",
            "audio_base_64": base64.b64encode(pcm.tobytes()).decode(),
            "commit": commit,
        }
        try:
            _ws.send(json.dumps(msg))
        except Exception as e:
            print(f"[stt] send error: {e}", flush=True)


def _recv_committed() -> str:
    """Read messages until committed_transcript, return text."""
    with _ws_lock:
        conn = _ws
    if conn is None:
        return ""
    try:
        while True:
            raw = conn.recv(timeout=10)
            data = json.loads(raw)
            mt = data.get("message_type", "")
            if mt == "committed_transcript":
                return data.get("text", "").strip()
            if "error" in mt:
                print(f"[stt] ws error: {data}", flush=True)
                return ""
    except Exception as e:
        print(f"[stt] recv error: {e}", flush=True)
        return ""


# ── audio ────────────────────────────────────────────────────────────────────

def _record_callback(indata, frames, time, status):
    _send_chunk(indata.copy())


# ── paste ────────────────────────────────────────────────────────────────────

def _paste(text: str) -> None:
    subprocess.run(["pbcopy"], input=text.encode(), check=True)
    subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to keystroke "v" using {command down}'],
        check=True,
    )


# ── state machine ────────────────────────────────────────────────────────────

def _start_recording() -> None:
    global _recording, _ws, _stream
    with _ws_lock:
        try:
            _ws = _connect()
            raw = _ws.recv(timeout=5)
            data = json.loads(raw)
            if data.get("message_type") != "session_started":
                print(f"[stt] unexpected: {data}", flush=True)
        except Exception as e:
            print(f"[stt] connect error: {e}", flush=True)
            _ws = None
            return

    _stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        callback=_record_callback,
    )
    _stream.start()

    with _lock:
        _recording = True
    print("[stt] ● nagrywanie...", flush=True)


def _stop_and_paste() -> None:
    global _recording, _ws, _stream
    with _lock:
        if not _recording:
            return
        _recording = False

    # stop mic first — orange dot disappears immediately
    if _stream:
        try:
            _stream.stop()
            _stream.close()
        except Exception:
            pass
        _stream = None

    # send final commit
    _send_chunk(np.zeros((1, CHANNELS), dtype=np.float32), commit=True)

    print("[stt] ◼ przetwarzanie...", flush=True)
    text = _recv_committed()

    with _ws_lock:
        if _ws:
            try:
                _ws.close()
            except Exception:
                pass
            _ws = None

    if text:
        print(f"[stt] → {text!r}", flush=True)
        _paste(text)
    else:
        print("[stt] (brak transkrypcji)", flush=True)


# ── hotkey listener ──────────────────────────────────────────────────────────

def _hotkey_active():
    return bool(_held & _CTRL) and bool(_held & _SHIFT)


def _on_press(key):
    _held.add(key)
    if not _recording and _hotkey_active():
        _start_recording()


def _on_release(key):
    _held.discard(key)
    if _recording and not _hotkey_active():
        threading.Thread(target=_stop_and_paste, daemon=True).start()


# ── main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not API_KEY:
        print("[stt] BŁĄD: ustaw ELEVENLABS_API_KEY", file=sys.stderr)
        sys.exit(1)

    print("[stt] gotowy — ctrl+shift żeby nagrywać (scribe_v2_realtime)", flush=True)
    with keyboard.Listener(on_press=_on_press, on_release=_on_release) as lst:
        lst.join()
