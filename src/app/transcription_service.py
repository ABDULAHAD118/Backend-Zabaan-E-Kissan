"""
Google Cloud Speech-to-Text Transcription Service
==================================================
Mirrors the logic from the Node.js transcription-service.js, ported to Python/FastAPI.
Setup Instructions:
1. Install dependency:
       pip install google-cloud-speech
2. Set up Google Cloud credentials:
   - Create a Google Cloud project at https://console.cloud.google.com
   - Enable the Speech-to-Text API
   - Create a service account and download the JSON key file
   - Export the path:
       export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-key.json"
3. Supported language codes examples:
       ur    -> Urdu
       en-US -> English (United States)
       pa-PK -> Punjabi (Pakistan)
"""
import os
import logging
logger = logging.getLogger(__name__)
# ---------------------------------------------------------------------------
# Encoding map - maps audio file extensions to Google Speech encoding names
# ---------------------------------------------------------------------------
ENCODING_MAP = {
    "wav":  "LINEAR16",
    "mp3":  "MP3",
    "m4a":  "MP4",
    "mp4":  "MP4",
    "ogg":  "OGG_OPUS",
    "webm": "WEBM_OPUS",
    "flac": "FLAC",
}
ALLOWED_MIMES = {
    "audio/wav",
    "audio/mpeg",
    "audio/mp4",
    "audio/m4a",
    "audio/ogg",
    "audio/webm",
    "audio/flac",
}
def _get_client():
    """Lazily create and return a Google Cloud SpeechClient."""
    try:
        from google.cloud import speech as gcp_speech
        client = gcp_speech.SpeechClient()
        logger.info("Google Cloud Speech-to-Text client initialized")
        return client
    except ImportError:
        logger.error(
            "google-cloud-speech is not installed. "
            "Run: pip install google-cloud-speech"
        )
        raise
    except Exception as exc:
        logger.error(
            "Failed to initialize Google Cloud Speech client: %s  "
            "Make sure GOOGLE_APPLICATION_CREDENTIALS is set correctly.",
            exc,
        )
        raise
def _detect_encoding(filename: str) -> str:
    """Return a Google Speech encoding name based on file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ENCODING_MAP.get(ext, "LINEAR16")
# ---------------------------------------------------------------------------
# Core transcription helpers
# ---------------------------------------------------------------------------
def transcribe_bytes(
    audio_bytes: bytes,
    filename: str,
    language: str = "ur",
    sample_rate: int = 16000,
    enable_punctuation: bool = True,
) -> dict:
    """
    Transcribe audio bytes using Google Cloud Speech-to-Text (synchronous recognize).
    Suitable for audio up to ~60 seconds / 10 MB.
    Parameters
    ----------
    audio_bytes:        Raw audio content.
    filename:           Original filename - used to detect encoding.
    language:           BCP-47 language code (default ur for Urdu).
    sample_rate:        Sample rate in Hz (default 16000).
    enable_punctuation: Whether to enable automatic punctuation.
    Returns
    -------
    dict with keys: transcript, language, confidence
    """
    from google.cloud import speech as gcp_speech
    client = _get_client()
    encoding_name = _detect_encoding(filename)
    encoding = getattr(gcp_speech.RecognitionConfig.AudioEncoding, encoding_name, None)
    if encoding is None:
        encoding = gcp_speech.RecognitionConfig.AudioEncoding.LINEAR16
    audio = gcp_speech.RecognitionAudio(content=audio_bytes)
    config = gcp_speech.RecognitionConfig(
        encoding=encoding,
        sample_rate_hertz=sample_rate,
        language_code=language,
        enable_automatic_punctuation=enable_punctuation,
        model="default",
    )
    logger.info("Processing synchronous transcription (language=%s) ...", language)
    response = client.recognize(config=config, audio=audio)
    transcript = ""
    confidence = 0.0
    if response.results:
        transcript = " ".join(
            result.alternatives[0].transcript for result in response.results
        )
        confidence = response.results[0].alternatives[0].confidence
    logger.info("Transcription complete: %d characters", len(transcript))
    return {
        "transcript": transcript,
        "language": language,
        "confidence": confidence,
    }
def transcribe_bytes_long(
    audio_bytes: bytes,
    filename: str,
    language: str = "ur",
    sample_rate: int = 16000,
    enable_punctuation: bool = True,
) -> dict:
    """
    Transcribe audio bytes using Google Cloud Speech-to-Text (longRunningRecognize).
    Suitable for audio longer than ~60 seconds.
    Returns
    -------
    dict with keys: transcript, language
    """
    from google.cloud import speech as gcp_speech
    client = _get_client()
    encoding_name = _detect_encoding(filename)
    encoding = getattr(gcp_speech.RecognitionConfig.AudioEncoding, encoding_name, None)
    if encoding is None:
        encoding = gcp_speech.RecognitionConfig.AudioEncoding.LINEAR16
    audio = gcp_speech.RecognitionAudio(content=audio_bytes)
    config = gcp_speech.RecognitionConfig(
        encoding=encoding,
        sample_rate_hertz=sample_rate,
        language_code=language,
        enable_automatic_punctuation=enable_punctuation,
    )
    logger.info("Starting long-running transcription (language=%s) ...", language)
    operation = client.long_running_recognize(config=config, audio=audio)
    logger.info("Waiting for long-running operation to complete ...")
    response = operation.result(timeout=300)
    transcript = ""
    if response.results:
        transcript = " ".join(
            result.alternatives[0].transcript for result in response.results
        )
    logger.info("Long-running transcription complete: %d characters", len(transcript))
    return {
        "transcript": transcript,
        "language": language,
    }
# ---------------------------------------------------------------------------
# Convenience wrapper that accepts a file path (mirrors Node.js readFileSync)
# ---------------------------------------------------------------------------
def transcribe_file(
    file_path: str,
    language: str = "ur",
    sample_rate: int = 16000,
    long_running: bool = False,
) -> dict:
    """
    Transcribe an audio file on disk.
    Parameters
    ----------
    file_path:    Absolute path to the audio file.
    language:     BCP-47 language code.
    sample_rate:  Sample rate in Hz.
    long_running: Use longRunningRecognize for files longer than 60 seconds.
    Returns
    -------
    dict with keys: transcript, language, (confidence for short audio)
    """
    filename = os.path.basename(file_path)
    with open(file_path, "rb") as fh:
        audio_bytes = fh.read()
    if long_running:
        return transcribe_bytes_long(audio_bytes, filename, language, sample_rate)
    return transcribe_bytes(audio_bytes, filename, language, sample_rate)
# ---------------------------------------------------------------------------
# Health helper
# ---------------------------------------------------------------------------
def is_client_available() -> bool:
    """Return True if the Google Cloud Speech client can be created."""
    try:
        _get_client()
        return True
    except Exception:
        return False
