from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Combined AI Analysis (Voice + Photo)
# ---------------------------------------------------------------------------
def analyse_incident_combined(
    short_description: str | None,
    detailed_description: str | None,
    voice_transcription: str | None,
    photo_analysis: dict | None,
    people_impacted: int,
    injury_reported: bool,
    immediate_danger: bool,
    location: str | None,
    site_name: str | None,
) -> dict:
    """Combined analysis using voice transcription and/or photo analysis."""
    
    # Build comprehensive incident context
    context_parts = []
    
    # Add basic info
    context_parts.append(f"Site: {site_name or 'Unknown'}")
    context_parts.append(f"Location: {location or 'Not specified'}")
    context_parts.append(f"People impacted: {people_impacted}")
    context_parts.append(f"Injury reported: {injury_reported}")
    context_parts.append(f"Immediate danger: {immediate_danger}")
    
    # Add text descriptions
    if short_description:
        context_parts.append(f"Short description: {short_description}")
    if detailed_description:
        context_parts.append(f"Detailed description: {detailed_description}")
    
    # Add voice transcription
    if voice_transcription:
        context_parts.append(f"Voice transcription: {voice_transcription}")
    
    # Add photo analysis
    if photo_analysis:
        context_parts.append(f"Photo description: {photo_analysis.get('description', 'No description')}")
        if photo_analysis.get('hazards_detected'):
            context_parts.append(f"Detected hazards: {', '.join(photo_analysis['hazards_detected'])}")
        if photo_analysis.get('missing_ppe'):
            context_parts.append(f"Missing PPE: {', '.join(photo_analysis['missing_ppe'])}")
        if photo_analysis.get('mismatch_flags'):
            context_parts.append(f"Warning flags: {', '.join(photo_analysis['mismatch_flags'])}")
    
    # Build user message
    user_msg = f"Incident Report:\n" + "\n".join(f"- {part}" for part in context_parts)
    
    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=800,
        )
        content = resp.choices[0].message.content
        logger.info("Combined AI analysis completed successfully")
        return json.loads(content)
    except Exception as e:
        logger.error(f"Combined AI analysis failed: {e}")
        raise

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment variables")
        
        # Log key details for debugging (masked)
        key = settings.openai_api_key
        logger.info("Creating OpenAI client with key: %s...%s (length: %d)", 
                   key[:10] if len(key) > 10 else key, 
                   key[-4:] if len(key) > 4 else key, 
                   len(key))
        
        _client = OpenAI(api_key=key)
    return _client


# ---------------------------------------------------------------------------
# 1. Analyse incident text  →  structured AI fields
# ---------------------------------------------------------------------------
EXTRACTION_SYSTEM = """You are an expert mining health & safety incident analyst for Glencore mining operations.
Given an incident report from a mine worker, extract and generate the following JSON object.
Be precise, concise and safety-focused. Use mining/H&S domain terminology.

Return ONLY valid JSON with these exact keys:
{
  "ai_title": "short descriptive title (max 15 words)",
  "ai_summary": "2-3 sentence executive summary",
  "ai_categories": ["list of categories, e.g. Slip/Fall, Equipment Hazard, Chemical Spill, Electrical, Fire, Structural, Vehicle, PPE Violation, Environmental"],
  "ai_severity": "Critical | High | Medium | Low",
  "ai_priority": "P1 | P2 | P3 | P4",
  "ai_confidence": 0.0 to 1.0,
  "ai_severity_rationale": "1-2 sentence explanation of why this severity was assigned",
  "ai_recommended_actions": ["list of 3-6 immediate recommended actions"],
  "ai_root_causes": ["list of 2-4 potential root causes"],
  "ai_extracted_entities": {
    "equipment": ["any equipment mentioned"],
    "substances": ["any chemicals/substances"],
    "body_parts_injured": ["any body parts"],
    "personnel_roles": ["any roles mentioned"],
    "environmental_factors": ["weather, terrain, etc."]
  },
  "ai_themes": ["1-3 broad safety themes, e.g. Slip & Fall Hazards, Equipment Maintenance, Chemical Safety, Electrical Safety, Structural Integrity, Vehicle Safety, PPE Compliance, Environmental Hazard, Confined Space, Working at Height, Fire & Explosion, Fatigue & Human Factors"]
}

Severity rules:
- Critical: fatality, multiple serious injuries, major structural collapse, uncontrolled fire/explosion, toxic gas release
- High: single serious injury, active danger present, major equipment failure, environmental spill
- Medium: minor injury, near-miss with potential for serious harm, equipment malfunction
- Low: no injury, minor property damage, observation/hazard report

Priority rules:
- P1: Critical severity OR immediate danger still active
- P2: High severity OR injury reported
- P3: Medium severity
- P4: Low severity
"""


def analyse_incident_text(
    short_description: str | None,
    detailed_description: str | None,
    people_impacted: int,
    injury_reported: bool,
    immediate_danger: bool,
    location: str | None,
    site_name: str | None,
) -> dict:
    """Call LLM to extract structured incident analysis from free text."""
    user_msg = f"""Incident Report:
- Site: {site_name or 'Unknown'}
- Location: {location or 'Not specified'}
- Short description: {short_description or 'None provided'}
- Detailed description: {detailed_description or 'None provided'}
- People impacted: {people_impacted}
- Injury reported: {injury_reported}
- Immediate danger: {immediate_danger}
"""
    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        return json.loads(raw)
    except Exception as e:
        logger.error("AI text analysis failed: %s", e)
        return _fallback_analysis(short_description, detailed_description, injury_reported, immediate_danger)


# ---------------------------------------------------------------------------
# 2. Analyse incident photo  →  hazard description
# ---------------------------------------------------------------------------
PHOTO_SYSTEM = """You are an expert mining health & safety visual analyst.
Analyse the uploaded incident photo from a mine site. Return ONLY valid JSON:
{
  "description": "what is visible in the photo (2-3 sentences)",
  "hazards_detected": ["list of visible hazards"],
  "mismatch_flags": ["anything that contradicts or is missing from the text report"],
  "missing_ppe": ["any missing PPE visible"],
  "raw_text": "any text/signs readable in the image"
}
Be factual. Do not speculate beyond what is visible. This is AI-assisted visual hazard interpretation, not forensic analysis."""


def analyse_photo(photo_path: str, incident_text: str = "") -> dict:
    """Use GPT-4o vision to analyse an incident photo."""
    try:
        client = _get_client()
        image_data = Path(photo_path).read_bytes()
        b64 = base64.b64encode(image_data).decode()

        ext = Path(photo_path).suffix.lower()
        mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}.get(ext, "image/jpeg")

        messages = [
            {"role": "system", "content": PHOTO_SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Incident text for cross-reference: {incident_text}" if incident_text else "No text report provided."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "low"}},
                ],
            },
        ]

        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
            max_tokens=800,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        logger.error("AI photo analysis failed: %s", e)
        return {
            "description": "Photo analysis unavailable.",
            "hazards_detected": [],
            "mismatch_flags": [],
            "missing_ppe": [],
            "raw_text": "",
        }


# ---------------------------------------------------------------------------
# 3. Transcribe voice to text (Whisper)
# ---------------------------------------------------------------------------
def transcribe_audio(audio_path: str) -> str:
    """Use OpenAI Whisper to transcribe an audio file to text.
    
    Raises on failure so the router can return a meaningful error.
    """
    client = _get_client()
    logger.info("Transcribing audio file: %s (size: %d bytes)", audio_path, Path(audio_path).stat().st_size)
    with open(audio_path, "rb") as audio_file:
        resp = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="en",
            prompt="Mining site safety incident report. Health and safety terminology.",
        )
    logger.info("Whisper response: %s", resp.text[:200] if resp.text else "(empty)")
    return resp.text


# ---------------------------------------------------------------------------
# 4. Photo pre-analysis → generate description to pre-fill form fields
# ---------------------------------------------------------------------------
PHOTO_PREFILL_SYSTEM = """You are an expert mining health & safety visual analyst for Glencore mining operations.
A mine worker has uploaded a photo of an incident BEFORE filling in the form.
Analyse the photo and return a JSON object that can pre-fill incident report fields.

Return ONLY valid JSON:
{
  "suggested_description": "A natural-language description of what happened based on the photo (2-4 sentences, written as if the worker is describing the incident)",
  "suggested_categories": ["likely incident categories based on what is visible"],
  "injury_likely": true/false,
  "immediate_danger_likely": true/false,
  "hazards_detected": ["list of visible hazards"],
  "missing_ppe": ["any missing PPE visible"],
  "suggested_location_type": "e.g. underground, open pit, workshop, haul road, processing plant, stockpile area",
  "visible_equipment": ["any equipment visible in the photo"],
  "confidence": 0.0 to 1.0
}

Be factual and concise. Write the suggested_description in plain worker language, not technical jargon.
This is AI-assisted interpretation to help the worker — they can edit it before submitting."""


def analyse_photo_for_prefill(photo_path: str) -> dict:
    """Use GPT-4o vision to analyse a photo and suggest form field values.
    
    Raises on failure so the router can return a meaningful error.
    """
    client = _get_client()
    image_data = Path(photo_path).read_bytes()
    b64 = base64.b64encode(image_data).decode()

    ext = Path(photo_path).suffix.lower()
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
            ".gif": "image/gif", ".webp": "image/webp"}.get(ext, "image/jpeg")

    logger.info("Analyzing photo for pre-fill: %s (size: %d bytes)", photo_path, len(image_data))

    messages = [
        {"role": "system", "content": PHOTO_PREFILL_SYSTEM},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "A mine worker just uploaded this photo of an incident. Analyse it to help pre-fill their report form."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "low"}},
            ],
        },
    ]

    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=800,
    )
    result = json.loads(resp.choices[0].message.content)
    logger.info("Photo pre-fill analysis successful: confidence=%.2f", result.get("confidence", 0))
    return result


# ---------------------------------------------------------------------------
# 5. Fallback (no API key or quota exceeded)
# ---------------------------------------------------------------------------
def _fallback_analysis(
    short_desc: str | None,
    detailed_desc: str | None,
    injury: bool,
    danger: bool,
) -> dict:
    """Rule-based fallback when AI is unavailable."""
    text = f"{short_desc or ''} {detailed_desc or ''}".lower()

    categories = []
    themes = []
    if any(w in text for w in ("slip", "fall", "trip", "wet")):
        categories.append("Slip/Fall")
        themes.append("Slip & Fall Hazards")
    if any(w in text for w in ("equipment", "machine", "loader", "truck", "conveyor", "drill")):
        categories.append("Equipment Hazard")
        themes.append("Equipment Maintenance")
    if any(w in text for w in ("fire", "smoke", "explosion", "burn")):
        categories.append("Fire/Explosion")
        themes.append("Fire & Explosion")
    if any(w in text for w in ("chemical", "spill", "leak", "gas", "toxic", "oil")):
        categories.append("Chemical/Spill")
        themes.append("Chemical Safety")
    if any(w in text for w in ("electric", "wire", "shock", "cable")):
        categories.append("Electrical")
        themes.append("Electrical Safety")
    if any(w in text for w in ("collapse", "crack", "structural", "roof", "wall")):
        categories.append("Structural")
        themes.append("Structural Integrity")
    if any(w in text for w in ("vehicle", "truck", "haul", "collision")):
        categories.append("Vehicle")
        themes.append("Vehicle Safety")
    if any(w in text for w in ("ppe", "helmet", "goggles", "gloves", "harness")):
        categories.append("PPE Violation")
        themes.append("PPE Compliance")
    if not categories:
        categories.append("General Hazard")
        themes.append("General Safety")

    if danger:
        severity, priority = "Critical", "P1"
    elif injury:
        severity, priority = "High", "P2"
    else:
        severity, priority = "Medium", "P3"

    return {
        "ai_title": (short_desc or "Incident report")[:80],
        "ai_summary": f"{short_desc or 'Incident reported.'} {detailed_desc or ''}".strip()[:300],
        "ai_categories": categories,
        "ai_severity": severity,
        "ai_priority": priority,
        "ai_confidence": 0.5,
        "ai_severity_rationale": f"Rule-based: injury={injury}, immediate_danger={danger}",
        "ai_recommended_actions": [
            "Investigate the area immediately",
            "Notify site safety officer",
            "Document findings with photos",
        ],
        "ai_root_causes": ["To be determined by investigation"],
        "ai_extracted_entities": {
            "equipment": [],
            "substances": [],
            "body_parts_injured": [],
            "personnel_roles": [],
            "environmental_factors": [],
        },
        "ai_themes": themes[:3],
    }
