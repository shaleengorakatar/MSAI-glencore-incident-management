from __future__ import annotations

from fastapi import APIRouter

from app.database import get_incidents_by_theme, get_themes_summary
from app.models.schemas import IncidentResponse, ThemeListResponse, ThemeSummary

router = APIRouter(prefix="/themes", tags=["Themes"])


# ---------------------------------------------------------------------------
# GET /api/themes  –  Thematic overview for managers
# ---------------------------------------------------------------------------
@router.get("", response_model=ThemeListResponse)
async def get_themes():
    """
    Returns all incident themes with counts, severity breakdown,
    affected sites, and a preview of recent incidents per theme.
    Managers click a theme card to drill down.
    """
    themes_data = get_themes_summary()
    themes = [ThemeSummary(**t) for t in themes_data]
    return ThemeListResponse(themes=themes, total_themes=len(themes))


# ---------------------------------------------------------------------------
# GET /api/themes/{theme_name}/incidents  –  Drill-down into a theme
# ---------------------------------------------------------------------------
@router.get("/{theme_name}/incidents", response_model=list[IncidentResponse])
async def get_theme_incidents(theme_name: str):
    """Return all incidents tagged with the given theme, sorted by priority."""
    incidents = get_incidents_by_theme(theme_name)
    return incidents
