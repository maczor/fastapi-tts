import os
from io import BytesIO

from dotenv import load_dotenv
from elevenlabs import AsyncElevenLabs
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
import uvicorn

load_dotenv()

api_key = os.getenv("ELEVENLABS_API_KEY")
if not api_key or api_key == "your-api-key-here":
    raise RuntimeError("ELEVENLABS_API_KEY is not set. Add it to .env file.")

client = AsyncElevenLabs(api_key=api_key)
app = FastAPI(title="FastAPI TTS Server")


class TTSRequest(BaseModel):
    text: str
    voice_id: str = "Cb8NLd0sUB8jI4MW2f9M"
    model_id: str = "eleven_v3"
    output_format: str = "mp3_44100_128"


@app.get("/voices")
async def list_voices():
    try:
        response = await client.voices.get_all()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return [{"voice_id": v.voice_id, "name": v.name} for v in response.voices]


@app.post("/tts")
async def text_to_speech(req: TTSRequest):
    try:
        audio = client.text_to_speech.convert(
            text=req.text,
            voice_id=req.voice_id,
            model_id=req.model_id,
            output_format=req.output_format,
        )
        buffer = BytesIO()
        async for chunk in audio:
            buffer.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return Response(content=buffer.getvalue(), media_type="audio/mpeg")


@app.post("/tts/stream")
async def text_to_speech_stream(req: TTSRequest):
    async def generate():
        try:
            audio = client.text_to_speech.convert(
                text=req.text,
                voice_id=req.voice_id,
                model_id=req.model_id,
                output_format=req.output_format,
            )
            async for chunk in audio:
                yield chunk
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))

    return StreamingResponse(generate(), media_type="audio/mpeg")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8008)
