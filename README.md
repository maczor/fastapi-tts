# FastAPI TTS Server

[PL](#pl) | [EN](#en)

---

<a id="en"></a>

A proxy to the ElevenLabs API exposing REST endpoints for text-to-speech conversion.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set your API key in `.env`:

```
ELEVENLABS_API_KEY=your-api-key-here
```

## Running

```bash
python main.py
```

Server starts on `0.0.0.0:8008`.

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/voices` | GET | List available voices |
| `/tts` | POST | TTS → audio file |
| `/tts/stream` | POST | TTS → streaming audio |

## Examples

```bash
curl http://localhost:8008/voices

curl -X POST http://localhost:8008/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, this is a test"}' --output speech.mp3

curl -X POST http://localhost:8008/tts/stream \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, this is a test"}' --output stream.mp3
```

## System audio playback

**afplay (macOS, built-in):**

```bash
curl -s -X POST http://localhost:8008/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, this is a test"}' --output /tmp/tts.mp3 && afplay /tmp/tts.mp3
```

**mpv (streaming, no temp file):**

```bash
brew install mpv
```

```bash
curl -s -X POST http://localhost:8008/tts/stream \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, this is a test"}' | mpv --no-terminal -
```

## System service (macOS)

Load the service (starts automatically on login):

```bash
launchctl load ~/Library/LaunchAgents/com.maczor.fastapi-tts.plist
```

Management:

```bash
# Stop
launchctl stop com.maczor.fastapi-tts

# Start
launchctl start com.maczor.fastapi-tts

# Status
launchctl list | grep fastapi-tts

# Unload permanently
launchctl unload ~/Library/LaunchAgents/com.maczor.fastapi-tts.plist

# Logs
tail -f ~/Library/Logs/fastapi-tts.log
```

## PAI TTS Bridge

A lightweight HTTP bridge that receives voice notification requests and plays them through the local TTS server using `mpv`.

```bash
python3 pai-tts-bridge.py
```

Listens on `[::1]:8888`. Forward the port via SSH to receive notifications from a remote server:

```bash
ssh -R 8888:localhost:8888 user@server
```

Send a notification:

```bash
curl -X POST http://[::1]:8888/notify \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello from the server"}'
```

## PAI STT (Speech-to-Text)

Push-to-talk transcription using ElevenLabs STT. Hold the hotkey, speak, release — the transcription is pasted into the active window.

```bash
python3 pai-stt.py
```

- **Hotkey:** `ctrl+shift` (hold to record, release to transcribe)
- Requires macOS Accessibility permissions for the terminal app
- Uses `pbcopy` + `osascript` to paste into the active window

---

<a id="pl"></a>

Proxy do ElevenLabs API udostępniający endpointy REST do konwersji tekstu na mowę.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ustaw klucz API w pliku `.env`:

```
ELEVENLABS_API_KEY=your-api-key-here
```

## Uruchomienie

```bash
python main.py
```

Serwer startuje na `0.0.0.0:8008`.

## Endpointy

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/voices` | GET | Lista dostępnych głosów |
| `/tts` | POST | TTS → plik audio |
| `/tts/stream` | POST | TTS → streaming audio |

## Przykłady

```bash
curl http://localhost:8008/voices

curl -X POST http://localhost:8008/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Cześć, to jest test"}' --output speech.mp3

curl -X POST http://localhost:8008/tts/stream \
  -H "Content-Type: application/json" \
  -d '{"text":"Cześć, to jest test"}' --output stream.mp3
```

## Odtwarzanie na systemowym audio

**afplay (macOS, wbudowany):**

```bash
curl -s -X POST http://localhost:8008/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Cześć, to jest test"}' --output /tmp/tts.mp3 && afplay /tmp/tts.mp3
```

**mpv (streaming, bez pliku tymczasowego):**

```bash
brew install mpv
```

```bash
curl -s -X POST http://localhost:8008/tts/stream \
  -H "Content-Type: application/json" \
  -d '{"text":"Cześć, to jest test"}' | mpv --no-terminal -
```

## Serwis systemowy (macOS)

Załaduj serwis (startuje automatycznie po zalogowaniu):

```bash
launchctl load ~/Library/LaunchAgents/com.maczor.fastapi-tts.plist
```

Zarządzanie:

```bash
# Wyłącz
launchctl stop com.maczor.fastapi-tts

# Włącz
launchctl start com.maczor.fastapi-tts

# Status
launchctl list | grep fastapi-tts

# Wyłącz na stałe
launchctl unload ~/Library/LaunchAgents/com.maczor.fastapi-tts.plist

# Logi
tail -f ~/Library/Logs/fastapi-tts.log
```

## PAI TTS Bridge

Lekki bridge HTTP — odbiera żądania powiadomień głosowych i odtwarza je przez lokalny serwer TTS przy użyciu `mpv`.

```bash
python3 pai-tts-bridge.py
```

Nasłuchuje na `[::1]:8888`. Przekieruj port przez SSH, aby odbierać powiadomienia ze zdalnego serwera:

```bash
ssh -R 8888:localhost:8888 user@server
```

Wyślij powiadomienie:

```bash
curl -X POST http://[::1]:8888/notify \
  -H "Content-Type: application/json" \
  -d '{"message":"Witaj z serwera"}'
```

## PAI STT (Speech-to-Text)

Transkrypcja push-to-talk z ElevenLabs STT. Trzymaj skrót, mów, puść — transkrypcja wkleja się w aktywne okno.

```bash
python3 pai-stt.py
```

- **Skrót:** `ctrl+shift` (trzymaj = nagrywanie, puść = transkrypcja)
- Wymaga uprawnień macOS Accessibility dla terminala
- Używa `pbcopy` + `osascript` do wklejania w aktywne okno
