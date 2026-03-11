from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.database import (
    count_incidents,
    get_incident,
    insert_incident,
    list_incidents,
    search_similar_text,
    update_incident,
)
from app.models.schemas import (
    IncidentListResponse,
    IncidentResponse,
    IncidentSubmission,
    IncidentUpdate,
    SimilarIncident,
    SimilarIncidentsResponse,
)
from app.services.ai_service import analyse_incident_text, analyse_photo

router = APIRouter(prefix="/incidents", tags=["Incidents"])


# ---------------------------------------------------------------------------
# POST /api/incidents  –  Submit a new incident (multipart form)
# ---------------------------------------------------------------------------
@router.post("", response_model=IncidentResponse, status_code=201)
async def create_incident(
    reporter_name: str = Form(...),
    site_name: str = Form(...),
    location: str = Form(None),
    reported_at: str = Form(None),
    short_description: str = Form(None),
    detailed_description: str = Form(None),
    people_impacted: int = Form(0),
    injury_reported: bool = Form(False),
    immediate_danger: bool = Form(False),
    photo: UploadFile | None = File(None),
):
    incident_id = str(uuid.uuid4())
    now = reported_at or datetime.now(timezone.utc).isoformat()

    # 1. Save Photo first (if exists) - using async file write
    photo_filename = None
    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        photo_filename = f"{incident_id}{ext}"
        photo_path = settings.upload_dir / photo_filename
        content = await photo.read()
        await run_in_threadpool(lambda: photo_path.write_bytes(content))

    # 2. Parallelize AI Tasks - run text and photo analysis simultaneously
    text_task = run_in_threadpool(
        analyse_incident_text,
        short_description,
        detailed_description,
        people_impacted,
        injury_reported,
        immediate_danger,
        location,
        site_name,
    )
    
    photo_task = None
    if photo_filename:
        incident_text = f"{short_description or ''} {detailed_description or ''}"
        photo_task = run_in_threadpool(
            analyse_photo,
            settings.upload_dir / photo_filename,
            incident_text,
        )

    # Wait for all AI results in parallel
    ai_data = await text_task
    photo_result = await photo_task if photo_task else {}

    # 3. Format Photo Analysis String
    photo_analysis_text = None
    if photo_result:
        photo_analysis_text = (
            f"Description: {photo_result.get('description', '')}\n"
            f"Hazards: {', '.join(photo_result.get('hazards_detected', []))}\n"
            f"Missing PPE: {', '.join(photo_result.get('missing_ppe', []))}\n"
            f"Mismatch flags: {', '.join(photo_result.get('mismatch_flags', []))}"
        )

    # 4. Save to DB - run in thread pool to avoid blocking
    record = {
        "id": incident_id,
        "reporter_name": reporter_name,
        "site_name": site_name,
        "location": location,
        "reported_at": now,
        "short_description": short_description,
        "detailed_description": detailed_description,
        "people_impacted": people_impacted,
        "injury_reported": int(injury_reported),
        "immediate_danger": int(immediate_danger),
        "photo_filename": photo_filename,
        "status": "open",
        **ai_data,
    }
    if photo_analysis_text:
        record["ai_photo_analysis"] = photo_analysis_text

    try:
        result = await run_in_threadpool(insert_incident, record)
        return result
    except Exception as e:
        # Cleanup orphaned photo if database insert fails
        if photo_filename:
            try:
                (settings.upload_dir / photo_filename).unlink(missing_ok=True)
            except Exception:
                pass  # Best effort cleanup
        raise HTTPException(status_code=500, detail=f"Failed to save incident: {str(e)}")


# ---------------------------------------------------------------------------
# POST /api/incidents/json  –  Submit via JSON body (no photo)
# ---------------------------------------------------------------------------
@router.post("/json", response_model=IncidentResponse, status_code=201)
async def create_incident_json(body: IncidentSubmission):
    """JSON-body endpoint for programmatic submission (no photo upload)."""
    incident_id = str(uuid.uuid4())
    now = body.reported_at or datetime.now(timezone.utc).isoformat()

    # Run AI analysis in thread pool
    ai_data = await run_in_threadpool(
        analyse_incident_text,
        body.short_description,
        body.detailed_description,
        body.people_impacted,
        body.injury_reported,
        body.immediate_danger,
        body.location,
        body.site_name,
    )

    record = {
        "id": incident_id,
        "reporter_name": body.reporter_name,
        "site_name": body.site_name,
        "location": body.location,
        "reported_at": now,
        "short_description": body.short_description,
        "detailed_description": body.detailed_description,
        "people_impacted": body.people_impacted,
        "injury_reported": int(body.injury_reported),
        "immediate_danger": int(body.immediate_danger),
        "photo_filename": None,
        "status": "open",
        **ai_data,
    }
    result = await run_in_threadpool(insert_incident, record)
    return result


# ---------------------------------------------------------------------------
# GET /api/incidents  –  List incidents with filters
# ---------------------------------------------------------------------------
@router.get("", response_model=IncidentListResponse)
async def get_incidents(
    status: str | None = None,
    severity: str | None = None,
    priority: str | None = None,
    site: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    # Run database queries in parallel
    incidents_task = run_in_threadpool(
        list_incidents,
        status=status,
        severity=severity,
        priority=priority,
        site=site,
        limit=limit,
        offset=offset,
    )
    total_task = run_in_threadpool(
        count_incidents,
        status=status,
        severity=severity,
        priority=priority,
        site=site,
    )
    
    incidents, total = await asyncio.gather(incidents_task, total_task)
    return IncidentListResponse(incidents=incidents, total=total, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# GET /api/incidents/{id}  –  Single incident detail
# ---------------------------------------------------------------------------
@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident_detail(incident_id: str):
    incident = await run_in_threadpool(get_incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


# ---------------------------------------------------------------------------
# PATCH /api/incidents/{id}  –  Update status / assignment
# ---------------------------------------------------------------------------
@router.patch("/{incident_id}", response_model=IncidentResponse)
async def patch_incident(incident_id: str, update: IncidentUpdate):
    existing = await run_in_threadpool(get_incident, incident_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Incident not found")

    data = update.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await run_in_threadpool(update_incident, incident_id, data)
    return result


# ---------------------------------------------------------------------------
# GET /api/incidents/{id}/similar  –  Similar incidents
# ---------------------------------------------------------------------------
@router.get("/{incident_id}/similar", response_model=SimilarIncidentsResponse)
async def get_similar_incidents(incident_id: str):
    incident = await run_in_threadpool(get_incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    search_text = f"{incident.get('ai_title', '')} {incident.get('short_description', '')} {incident.get('detailed_description', '')}"
    similar_raw = await run_in_threadpool(
        search_similar_text, search_text, exclude_id=incident_id, limit=5
    )

    similar = [
        SimilarIncident(
            id=s["id"],
            ai_title=s.get("ai_title"),
            ai_severity=s.get("ai_severity"),
            ai_priority=s.get("ai_priority"),
            site_name=s.get("site_name", "Unknown"),
            reported_at=s.get("reported_at", ""),
            ai_categories=s.get("ai_categories"),
        )
        for s in similar_raw
    ]
    return SimilarIncidentsResponse(similar=similar)
