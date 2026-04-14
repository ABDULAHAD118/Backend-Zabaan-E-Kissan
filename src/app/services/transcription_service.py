"""
Audio transcription service using OpenAI Whisper API.
"""
import logging
import os
import tempfile
from typing import Optional
from openai import OpenAI
from ..core import config
import boto3
import uuid
import time
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

logger = logging.getLogger(__name__)
def transcribe_audio(audio_bytes: bytes, filename: str, language: Optional[str] = None) -> dict:
    """
    Transcribe audio bytes using the OpenAI Whisper API.
    Args:
        audio_bytes: Raw bytes of the audio file.
        filename:    Original filename (used to derive file extension).
        language:    BCP-47 language code (e.g. "ur", "en"). If None, Whisper
                     auto-detects the language.
    Returns:
        dict with keys ``transcript`` and ``text``.
    Raises:
        ValueError:  If OPENAI_API_KEY is not configured.
        RuntimeError: On transcription failure.
    """

    if not config.OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY is not set. Configure it in your environment variables."
        )
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    # Derive file extension from original filename
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "m4a"
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as audio_file:
            params: dict = {
                "model": config.WHISPER_MODEL,
                "file": audio_file,
                "response_format": "json",
            }
            lang = (language or config.WHISPER_DEFAULT_LANGUAGE).strip()
            if lang:
                params["language"] = lang
            response = client.audio.transcriptions.create(**params)
        transcript_text: str = response.text
        logger.info(
            "✅ Transcription complete: %d chars, language=%s",
            len(transcript_text),
            lang,
        )
        return {"transcript": transcript_text, "text": transcript_text}
    except Exception as exc:
        logger.error("Transcription failed: %s", exc)
        raise RuntimeError(str(exc)) from exc
    finally:
        try:
            os.unlink(tmp_path)
        except OSError as exc:
            logger.warning("Could not delete temp file %s: %s", tmp_path, exc)

def transcribe_audio_hf(audio_bytes: bytes, filename: str, language: Optional[str] = None) -> dict:
    """
    Transcribe audio bytes using HuggingFace Whisper pipeline.
    Keeps existing OpenAI-based method untouched.
    """
    if not audio_bytes:
        raise ValueError("Audio content is empty.")

    requested_language = (language or config.WHISPER_DEFAULT_LANGUAGE).strip() or None
    resolved_device =  "cpu"
    torch_dtype = torch.float32

    ext = filename.rsplit(".", 1)[-1] if "." in filename else "mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            config.HF_WHISPER_MODEL_ID,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
        )
        processor = AutoProcessor.from_pretrained(config.HF_WHISPER_MODEL_ID)

        asr_pipeline = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=resolved_device,
            return_timestamps=config.HF_WHISPER_RETURN_TIMESTAMPS,
        )

        generate_kwargs = {"language": requested_language} if requested_language else None
        result = asr_pipeline(tmp_path, generate_kwargs=generate_kwargs)
        transcript_text = (result or {}).get("text", "").strip()

        logger.info(
            "HF transcription complete: %d chars, model=%s, device=%s, language=%s",
            len(transcript_text),
            config.HF_WHISPER_MODEL_ID,
            resolved_device,
            requested_language,
        )
        return {"transcript": transcript_text, "text": transcript_text, "raw": result}
    except Exception as exc:
        logger.error("HF transcription failed: %s", exc)
        raise RuntimeError(str(exc)) from exc
    finally:
        try:
            os.unlink(tmp_path)
        except OSError as exc:
            logger.warning("Could not delete temp file %s: %s", tmp_path, exc)

