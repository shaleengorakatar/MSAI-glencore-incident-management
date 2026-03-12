from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Incident Submission (Worker side)
# ---------------------------------------------------------------------------
class IncidentSubmission(BaseModel):
    reporter_name: str = Field(..., min_length=1, max_length=200)
    site_name: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = Field(None, max_length=500)
    reported_at: Optional[str] = None  # ISO datetime string; defaults to now
    short_description: Optional[str] = Field(None, max_length=1000)
    detailed_description: Optional[str] = None
    people_impacted: int = 0
    injury_reported: bool = False
    immediate_danger: bool = False


# ---------------------------------------------------------------------------
# AI-generated analysis returned after submission
# ---------------------------------------------------------------------------
class AIAnalysis(BaseModel):
    ai_title: str
    ai_summary: str
    ai_categories: list[str]
    ai_severity: str  # Critical / High / Medium / Low
    ai_priority: str  # P1 / P2 / P3 / P4
    ai_confidence: float = Field(ge=0, le=1)
    ai_severity_rationale: str
    ai_recommended_actions: list[str]
    ai_root_causes: list[str]
    ai_extracted_entities: dict
    ai_themes: list[str]


class PhotoAnalysis(BaseModel):
    description: str
    hazards_detected: list[str]
    mismatch_flags: list[str]
    missing_ppe: list[str]
    raw_text: str


# ---------------------------------------------------------------------------
# Full incident response (includes AI fields)
# ---------------------------------------------------------------------------
class IncidentResponse(BaseModel):
    id: str
    reporter_name: str
    site_name: str
    location: Optional[str] = None
    reported_at: str
    short_description: Optional[str] = None
    detailed_description: Optional[str] = None
    people_impacted: int = 0
    injury_reported: bool = False
    immediate_danger: bool = False
    photo_filename: Optional[str] = None
    status: str = "open"

    ai_title: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_categories: Optional[list[str]] = None
    ai_severity: Optional[str] = None
    ai_priority: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_severity_rationale: Optional[str] = None
    ai_recommended_actions: Optional[list[str]] = None
    ai_root_causes: Optional[list[str]] = None
    ai_photo_analysis: Optional[str] = None
    ai_extracted_entities: Optional[dict] = None
    ai_themes: Optional[list[str]] = None

    assigned_to: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class IncidentListResponse(BaseModel):
    incidents: list[IncidentResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Incident update (Manager side)
# ---------------------------------------------------------------------------
class IncidentUpdate(BaseModel):
    status: Optional[str] = None  # open / in_review / assigned / escalated / closed
    assigned_to: Optional[str] = None
    ai_priority: Optional[str] = None  # P1 | P2 | P3 | P4
    ai_severity: Optional[str] = None  # Critical | High | Medium | Low


# ---------------------------------------------------------------------------
# Theme / Thematic view
# ---------------------------------------------------------------------------
class SeverityBreakdown(BaseModel):
    Critical: int = 0
    High: int = 0
    Medium: int = 0
    Low: int = 0


class ThemeSummary(BaseModel):
    theme: str
    total_count: int
    severity_breakdown: SeverityBreakdown
    open_count: int
    sites_affected: list[str]
    recent_incidents: list[dict]


class ThemeListResponse(BaseModel):
    themes: list[ThemeSummary]
    total_themes: int


# ---------------------------------------------------------------------------
# Similar incidents
# ---------------------------------------------------------------------------
class SimilarIncident(BaseModel):
    id: str
    ai_title: Optional[str] = None
    ai_severity: Optional[str] = None
    ai_priority: Optional[str] = None
    site_name: str
    reported_at: str
    ai_categories: Optional[list[str]] = None


class SimilarIncidentsResponse(BaseModel):
    similar: list[SimilarIncident]


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------
class DashboardStats(BaseModel):
    total_incidents: int
    open_incidents: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    injury_count: int
    active_danger_count: int
    sites: list[str]
