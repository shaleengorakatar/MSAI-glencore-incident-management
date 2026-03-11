from __future__ import annotations

import logging
import os
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.services.ai_service import analyse_photo_for_prefill, transcribe_audio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Utilities"])


@router.get("/debug")
async def debug_api_key():
    """Debug endpoint to check if OpenAI API key is loaded."""
    key = settings.openai_api_key
    masked = key[:10] + "..." + key[-4:] if key and len(key) > 14 else "NOT_SET"
    return {
        "api_key_set": bool(key),
        "api_key_length": len(key) if key else 0,
        "api_key_preview": masked,
        "openai_model": settings.openai_model,
    }


# ---------------------------------------------------------------------------
# POST /api/ai/transcribe  –  Voice-to-text (Whisper)
# ---------------------------------------------------------------------------
@router.post("/transcribe")
async def voice_to_text(audio: UploadFile = File(...)):
    """
    Accept an audio file (webm, mp3, wav, m4a, ogg) from the browser's
    MediaRecorder and return the transcribed text via OpenAI Whisper.
    """
    allowed = {".webm", ".mp3", ".wav", ".m4a", ".ogg", ".mp4", ".mpeg", ".mpga"}
    ext = os.path.splitext(audio.filename or "recording.webm")[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {ext}")

    content = await audio.read()
    if not content or len(content) < 100:
        raise HTTPException(status_code=400, detail=f"Audio file is empty or too small ({len(content)} bytes)")

    logger.info("Received audio: filename=%s, size=%d bytes, ext=%s", audio.filename, len(content), ext)

    # Save to uploads dir (Render's temp dir can be read-only)
    os.makedirs(settings.upload_dir, exist_ok=True)
    tmp_path = os.path.join(settings.upload_dir, f"voice_{uuid.uuid4()}{ext}")
    try:
        with open(tmp_path, "wb") as f:
            f.write(content)

        transcript = transcribe_audio(tmp_path)
        if not transcript:
            raise HTTPException(
                status_code=500,
                detail="Transcription returned empty. Check that OPENAI_API_KEY is set and the audio contains speech.",
            )

        logger.info("Transcription successful: %d chars", len(transcript))
        return {"transcript": transcript}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Transcription endpoint error: %s", e)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ---------------------------------------------------------------------------
# POST /api/ai/analyze-photo  –  Photo pre-analysis to pre-fill form
# ---------------------------------------------------------------------------
@router.post("/analyze-photo")
async def analyze_photo_prefill(photo: UploadFile = File(...)):
    """
    Accept an incident photo and return AI-suggested form field values.
    The frontend uses this to pre-fill the description, injury toggle,
    danger toggle, etc. before the worker submits.
    """
    allowed = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ext = os.path.splitext(photo.filename or "photo.jpg")[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported image format: {ext}")

    content = await photo.read()
    if not content or len(content) < 500:
        raise HTTPException(status_code=400, detail=f"Image file is empty or too small ({len(content)} bytes)")

    logger.info("Received photo: filename=%s, size=%d bytes, ext=%s", photo.filename, len(content), ext)

    os.makedirs(settings.upload_dir, exist_ok=True)
    tmp_filename = f"prefill_{uuid.uuid4()}{ext}"
    tmp_path = os.path.join(settings.upload_dir, tmp_filename)
    try:
        with open(tmp_path, "wb") as f:
            f.write(content)

        result = analyse_photo_for_prefill(tmp_path)
        if not result or not result.get("suggested_description"):
            raise HTTPException(
                status_code=500,
                detail="Photo analysis returned empty. Check that OPENAI_API_KEY is set and the image contains visible content.",
            )

        logger.info("Photo analysis successful: confidence=%.2f, description_len=%d", result.get("confidence", 0), len(result.get("suggested_description", "")))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Photo analysis endpoint error: %s", e)
        raise HTTPException(status_code=500, detail=f"Photo analysis failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
