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
    # provider = getattr(config, "TRANSCRIBE_PROVIDER", "openai")
    # print('Provider',provider)
    # if provider == "aws":
    #     return transcribe_audio_aws(audio_bytes, filename, language or "ur")

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

def transcribe_audio_aws(audio_bytes: bytes, filename: str, language: str = "ur") -> dict:
    """
    Transcribe audio using Amazon Transcribe.
    """
    s3 = boto3.client(
        "s3",
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        region_name=config.AWS_REGION,
    )

    transcribe = boto3.client(
        "transcribe",
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        region_name=config.AWS_REGION,
    )

    bucket = config.AWS_TRANSCRIBE_BUCKET
    job_name = f"transcription-{uuid.uuid4()}"

    ext = filename.rsplit(".", 1)[-1] if "." in filename else "wav"
    key = f"uploads/{job_name}.{ext}"

    # Upload audio to S3
    s3.put_object(Bucket=bucket, Key=key, Body=audio_bytes)

    media_uri = f"s3://{bucket}/{key}"

    # Start transcription job
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": media_uri},
        MediaFormat=ext,
        LanguageCode=language,
    )

    # Wait for job completion
    while True:
        status = transcribe.get_transcription_job(
            TranscriptionJobName=job_name
        )

        job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]

        if job_status in ["COMPLETED", "FAILED"]:
            break

        time.sleep(2)

    if job_status == "FAILED":
        raise RuntimeError("AWS transcription failed")

    transcript_uri = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]

    import requests
    transcript_json = requests.get(transcript_uri).json()

    transcript_text = transcript_json["results"]["transcripts"][0]["transcript"]

    return {"transcript": transcript_text, "text": transcript_text}