"""Speech-to-Text service using local faster-whisper or OpenAI Whisper API."""

import base64
import tempfile
import os
import logging
from config import settings

logger = logging.getLogger(__name__)

# ── Whisper model singleton (loaded once, reused) ─────────────────
_whisper_model = None

def _get_whisper_model():
    """Lazy-load and cache the WhisperModel so it's not reloaded on every call."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        logger.info(f"Loading Whisper model: {settings.WHISPER_LOCAL_MODEL}")
        _whisper_model = WhisperModel(
            settings.WHISPER_LOCAL_MODEL, device="cpu", compute_type="int8"
        )
        logger.info("Whisper model loaded.")
    return _whisper_model


def warm_up() -> None:
    """Preload the Whisper model in the background (only for local mode)."""
    if settings.WHISPER_MODE != "local":
        return
    try:
        _get_whisper_model()
        logger.info("Whisper model ready ✓")
    except Exception as e:
        logger.warning(f"Whisper warm-up skipped: {e}")


async def transcribe_audio(audio_base64: str, mime_type: str = "audio/webm") -> str:
    """Transcribe audio using Whisper (local or API)."""
    audio_bytes = base64.b64decode(audio_base64)

    # Normalize mime type (browser may send "audio/webm;codecs=opus" etc)
    mime_base = mime_type.split(";")[0].strip().lower() if mime_type else "audio/webm"
    ext_map = {
        "audio/webm": ".webm", "audio/mp4": ".mp4", "audio/wav": ".wav",
        "audio/ogg": ".ogg", "audio/mpeg": ".mp3", "audio/mp3": ".mp3",
    }
    ext = ext_map.get(mime_base, ".webm")

    if settings.WHISPER_MODE == "local":
        return await _transcribe_local(audio_bytes, ext)
    else:
        return await _transcribe_openai_api(audio_bytes, ext, mime_type)


async def _transcribe_local(audio_bytes: bytes, ext: str) -> str:
    """Transcribe using cached local faster-whisper model."""
    try:
        model = _get_whisper_model()
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        try:
            segments, _ = model.transcribe(
                tmp_path,
                beam_size=5,
                language="en",                 # interviews are in English (en-IN)
                vad_filter=True,                # drop silence → fewer hallucinations
                vad_parameters=dict(min_silence_duration_ms=500),
                condition_on_previous_text=False,
                temperature=0.0,                # deterministic, most accurate
            )
            return " ".join(seg.text for seg in segments).strip()
        finally:
            os.unlink(tmp_path)
    except ImportError:
        logger.warning("faster-whisper not installed — returning placeholder")
        return "[Transcription unavailable — install faster-whisper]"
    except Exception as e:
        logger.error(f"Local transcription error: {e}")
        raise


async def _transcribe_openai_api(audio_bytes: bytes, ext: str, mime_type: str) -> str:
    """Transcribe using OpenAI Whisper API."""
    import httpx
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            with open(tmp_path, "rb") as audio_file:
                resp = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    files={"file": (f"audio{ext}", audio_file, mime_type)},
                    data={"model": "whisper-1"},
                )
        resp.raise_for_status()
        return resp.json()["text"]
    finally:
        os.unlink(tmp_path)