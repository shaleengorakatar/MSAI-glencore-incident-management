from __future__ import annotations

import logging
import os
import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.services.ai_service import analyse_photo_for_prefill, transcribe_audio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Utilities"])


@router.get("/debug")
async def debug_api_key():
    """Debug endpoint to check if OpenAI API key is loaded. Development only."""
    # Only allow in development - remove this check if you need it in production
    if not settings.environment.startswith("dev"):
        raise HTTPException(status_code=404, detail="Not found")
    
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

    # Stream directly to disk (memory efficient)
    tmp_path = settings.upload_dir / f"voice_{uuid.uuid4()}{ext}"
    try:
        with open(tmp_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        
        # Check file size after streaming
        file_size = os.path.getsize(tmp_path)
        if file_size < 100:
            raise HTTPException(status_code=400, detail=f"Audio file is empty or too small ({file_size} bytes)")
        
        logger.info("Received audio: filename=%s, size=%d bytes, ext=%s", audio.filename, file_size, ext)

        # Offload blocking AI call to thread pool
        transcript = await run_in_threadpool(transcribe_audio, tmp_path)
        
        # Validate transcription result
        if not transcript or len(transcript.strip()) < 3:
            raise HTTPException(
                status_code=500,
                detail="Transcription returned empty or too short. Ensure the audio contains clear speech.",
            )
        
        # Check for common Whisper hallucinations with silent audio
        hallucination_phrases = ["thank you for watching", "please subscribe", "like and subscribe", "don't forget to", "background music"]
        transcript_lower = transcript.lower()
        if any(phrase in transcript_lower for phrase in hallucination_phrases):
            raise HTTPException(
                status_code=500,
                detail="Audio appears to be silent or contains background music. Please record clear speech.",
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

    # Stream directly to disk (memory efficient)
    tmp_filename = f"prefill_{uuid.uuid4()}{ext}"
    tmp_path = settings.upload_dir / tmp_filename
    try:
        with open(tmp_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        
        # Check file size after streaming
        file_size = os.path.getsize(tmp_path)
        if file_size < 500:
            raise HTTPException(status_code=400, detail=f"Image file is empty or too small ({file_size} bytes)")
        
        logger.info("Received photo: filename=%s, size=%d bytes, ext=%s", photo.filename, file_size, ext)

        # Offload blocking AI call to thread pool
        result = await run_in_threadpool(analyse_photo_for_prefill, tmp_path)
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
