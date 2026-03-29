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
    pass

TTS_URL = "http://localhost:8008/tts/stream"
BRIDGE_PORT = 8888

_speech_queue: queue.Queue[dict] = queue.Queue()


def _worker() -> None:
    while True:
        item = _speech_queue.get()
        try:
            body = json.dumps(item).encode()
            req = urllib.request.Request(
                TTS_URL,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                proc = subprocess.Popen(
                    ["/opt/homebrew/bin/mpv", "--no-terminal", "--demuxer=lavf", "-"],
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
        except Exception as e:
            print(f"[bridge] invalid JSON: {e}", flush=True)
            self._json_error(400, f"invalid JSON: {e}")
            return

        message = data.get("message", "")
        voice_enabled = data.get("voice_enabled", True)
        voice_id = data.get("voice_id")

        if voice_enabled and message:
            item = {"text": message}
            if voice_id:
                item["voice_id"] = voice_id
            _speech_queue.put(item)

        self.send_response(200)
        self.end_headers()

    def _json_error(self, code: int, message: str) -> None:
        body = json.dumps({"error": message}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"[bridge] {fmt % args}", flush=True)


if __name__ == "__main__":
    server = _Bridge(("127.0.0.1", BRIDGE_PORT), Handler)
    print(f"[bridge] listening on 127.0.0.1:{BRIDGE_PORT} → TTS at {TTS_URL}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[bridge] stopped")
