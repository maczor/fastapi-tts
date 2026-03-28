# FastAPI TTS Server

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
