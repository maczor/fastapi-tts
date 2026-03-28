#!/usr/bin/env python3
"""
PAI STT — push-to-talk na Macu, wkleja transkrypcję do aktywnego okna.

Wymagania:
    pip install sounddevice numpy pynput requests

Uprawnienia macOS:
    System Settings → Privacy & Security → Accessibility → dodaj swój terminal lub Python

Konfiguracja:
    export ELEVENLABS_API_KEY=your_key

Użycie:
    python3 pai-stt.py &
    Trzymaj ctrl+shift → mów → puść → tekst pojawia się w aktywnym oknie
"""

import concurrent.futures
import io
import os
import subprocess
import sys
import threading
import wave

import numpy as np
import requests
import sounddevice as sd
from pynput import keyboard
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
SAMPLE_RATE = 16000
CHANNELS = 1

_recording = False
_chunks: list[np.ndarray] = []
_lock = threading.Lock()

_CTRL  = {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}
_SHIFT = {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r}
_held: set = set()

_session = requests.Session()
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


# ── audio ─────────────────────────────────────────────────────────────────────

def _record_callback(indata, frames, time, status):
    with _lock:
        if _recording:
            _chunks.append(indata.copy())


def _to_wav(chunks: list[np.ndarray]) -> bytes:
    audio = np.concatenate(chunks, axis=0)
    pcm = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(np.dtype(np.int16).itemsize)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


# ── transcription + paste ─────────────────────────────────────────────────────

def _transcribe(wav_bytes: bytes) -> str:
    resp = _session.post(
        "https://api.elevenlabs.io/v1/speech-to-text",
        headers={"xi-api-key": API_KEY},
        files={"file": ("audio.wav", wav_bytes, "audio/wav")},
        data={"model_id": "scribe_v1"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("text", "").strip()


def _paste(text: str) -> None:
    subprocess.run(["pbcopy"], input=text.encode(), check=True)
    subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to keystroke "v" using {command down}'],
        check=True,
    )


# ── state machine ─────────────────────────────────────────────────────────────

def _start_recording() -> None:
    global _recording
    with _lock:
        _chunks.clear()
        _recording = True
    print("[stt] ● nagrywanie...", flush=True)


def _process() -> None:
    global _recording
    with _lock:
        if not _recording:
            return                  # another release already handled this
        _recording = False
        chunks = list(_chunks)
        _chunks.clear()

    if not chunks or len(np.concatenate(chunks)) < SAMPLE_RATE * 0.3:
        print("[stt] (za krótkie nagranie, pomiń)", flush=True)
        return

    print("[stt] ◼ przetwarzanie...", flush=True)
    try:
        text = _transcribe(_to_wav(chunks))
        if text:
            print(f"[stt] → {text!r}", flush=True)
            _paste(text)
        else:
            print("[stt] (brak transkrypcji)", flush=True)
    except requests.HTTPError as e:
        print(f"[stt] API error: {e}", flush=True)
    except Exception as e:
        print(f"[stt] błąd: {e}", flush=True)


# ── hotkey listener ───────────────────────────────────────────────────────────

def _hotkey_active():
    return bool(_held & _CTRL) and bool(_held & _SHIFT)


def _on_press(key):
    _held.add(key)
    if not _recording and _hotkey_active():
        _start_recording()


def _on_release(key):
    _held.discard(key)
    if _recording and not _hotkey_active():
        _executor.submit(_process)


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not API_KEY:
        print("[stt] BŁĄD: ustaw ELEVENLABS_API_KEY", file=sys.stderr)
        sys.exit(1)

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        callback=_record_callback,
    ):
        print("[stt] gotowy — ctrl+shift żeby nagrywać", flush=True)
        with keyboard.Listener(on_press=_on_press, on_release=_on_release) as lst:
            lst.join()
