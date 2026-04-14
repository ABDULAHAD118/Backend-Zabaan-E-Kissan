"""
Google Transcription router.
POST /transcribe/google – Convert an uploaded audio file to text via Google Cloud Speech-to-Text.
"""
import logging
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from ..services.google_transcription_service import transcribe_audio_google

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcribe/google", tags=["Transcription"])


@router.post(
    "",
    summary="Transcribe audio to text (Google)",
    description=(
        "Upload an audio file (M4A, MP3, WAV, FLAC, OGG, WebM) and receive a text transcription "
        "using Google Cloud Speech-to-Text API. Defaults to Urdu Pakistan ('ur-PK'). "
        "Supports any BCP-47 language code."
    ),
)
async def transcribe_google(
    audio: UploadFile = File(..., description="Audio file to transcribe"),
    language: str = Form(default="ur-PK", description="BCP-47 language code (default: 'ur-PK')"),
):
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

    try:
        result = transcribe_audio_google(
            audio_bytes=audio_bytes,
            filename=audio.filename or "audio.m4a",
            language=language or None,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}")
