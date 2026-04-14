"""
Audio transcription service using Google Cloud Speech-to-Text API.
"""
import logging
import os
import tempfile
from typing import Optional
from google.cloud import speech
from ..core import config

logger = logging.getLogger(__name__)


def transcribe_audio_google(audio_bytes: bytes, filename: str, language: Optional[str] = None) -> dict:
    """
    Transcribe audio bytes using Google Cloud Speech-to-Text API.

    Args:
        audio_bytes: Raw bytes of the audio file.
        filename:    Original filename (used to derive file extension).
        language:    BCP-47 language code (e.g. "ur-PK", "en-US"). If None,
                     uses the default from config.

    Returns:
        dict with keys ``transcript`` and ``text``.

    Raises:
        ValueError:  If GOOGLE_APPLICATION_CREDENTIALS is not configured.
        RuntimeError: On transcription failure.
    """
    if not config.GOOGLE_APPLICATION_CREDENTIALS:
        raise ValueError(
            "GOOGLE_APPLICATION_CREDENTIALS is not set. "
            "Set the path to your service account JSON key file."
        )

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "m4a"
    mime_type_map = {
        "mp3": "audio/mp3",
        "wav": "audio/wav",
        "flac": "audio/flac",
        "ogg": "audio/ogg",
        "m4a": "audio/m4a",
        "webm": "audio/webm",
    }
    mime_type = mime_type_map.get(ext, "audio/mp3")

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        client = speech.SpeechClient()

        with open(tmp_path, "rb") as audio_file:
            audio_content = audio_file.read()

        lang = (language or config.GOOGLE_SPEECH_DEFAULT_LANGUAGE).strip()

        audio = speech.RecognitionAudio(content=audio_content)
        config_gcp = speech.RecognitionConfig(
            encoding=getattr(speech.RecognitionConfig.AudioEncoding, {
                "mp3": "MP3",
                "wav": "LINEAR16",
                "flac": "FLAC",
                "ogg": "OGG_OPUS",
                "m4a": "MP3",
                "webm": "WEBM_OPUS",
            }.get(ext, "MP3"), speech.RecognitionConfig.AudioEncoding.MP3),
            sample_rate_hertz=16000,
            language_code=lang,
            model=config.GOOGLE_SPEECH_MODEL,
            enable_automatic_punctuation=True,
        )

        response = client.recognize(config=config_gcp, audio=audio)

        if not response.results:
            logger.warning("No transcription results returned from Google API.")
            transcript_text = ""
        else:
            transcript_text = response.results[0].alternatives[0].transcript

        logger.info(
            "✅ Google Transcription complete: %d chars, language=%s",
            len(transcript_text),
            lang,
        )
        return {"transcript": transcript_text, "text": transcript_text}

    except Exception as exc:
        logger.error("Google Transcription failed: %s", exc)
        raise RuntimeError(str(exc)) from exc
    finally:
        try:
            os.unlink(tmp_path)
        except OSError as exc:
            logger.warning("Could not delete temp file %s: %s", tmp_path, exc)
