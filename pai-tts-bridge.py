#!/usr/bin/env python3
"""
PAI TTS Bridge — runs on Mac, port 8888
Receives PAI voice notifications and plays them via local TTS service + mpv.

Usage:
    python3 pai-tts-bridge.py
    python3 pai-tts-bridge.py &   # background

SSH tunnel (add to ~/.ssh/config or use flag):
    ssh -R 8888:localhost:8888 user@server
"""

import json
import queue
import shutil
import socket
import subprocess
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer


class _Bridge(HTTPServer):
    address_family = socket.AF_INET6

TTS_URL = "http://localhost:8008/tts/stream"
BRIDGE_PORT = 8888

_speech_queue: queue.Queue[str] = queue.Queue()


def _worker() -> None:
    while True:
        text = _speech_queue.get()
        try:
            body = json.dumps({"text": text}).encode()
            req = urllib.request.Request(
                TTS_URL,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                proc = subprocess.Popen(
                    ["mpv", "--no-terminal", "--demuxer=lavf", "-"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                shutil.copyfileobj(resp, proc.stdin)
                proc.stdin.close()
                proc.wait()
        except urllib.error.URLError as e:
            print(f"[bridge] TTS unreachable: {e}")
        except Exception as e:
            print(f"[bridge] playback error: {e}")
        finally:
            _speech_queue.task_done()


threading.Thread(target=_worker, daemon=True, name="speech-worker").start()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/notify":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        try:
            data = json.loads(raw)
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        message = data.get("message", "")
        voice_enabled = data.get("voice_enabled", True)

        if voice_enabled and message:
            _speech_queue.put(message)

        self.send_response(200)
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    server = _Bridge(("::1", BRIDGE_PORT), Handler)
    print(f"[bridge] listening on ::1:{BRIDGE_PORT} → TTS at {TTS_URL}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[bridge] stopped")
