"""
Transcription router.
POST /transcribe – Convert an uploaded audio file to text via OpenAI Whisper.
"""
import logging
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from ..services.transcription_service import transcribe_audio, transcribe_audio_hf
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transcribe", tags=["Transcription"])
@router.post(
    "",
    summary="Transcribe audio to text",
    description=(
        "Upload an audio file (M4A, MP3, WAV, etc.) and receive a text transcription. "
        "Defaults to Urdu ('ur'). Supports any language code recognised by OpenAI Whisper."
    ),
)
async def transcribe(
    audio: UploadFile = File(..., description="Audio file to transcribe"),
    language: str = Form(default="ur", description="BCP-47 language code (default: 'ur')"),
):
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")
    try:
        result = transcribe_audio_hf(
            audio_bytes=audio_bytes,
            filename=audio.filename or "audio.m4a",
            language=language or None,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}")
