from __future__ import annotations

from fastapi import APIRouter

from app.database import count_incidents, list_incidents
from app.models.schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Aggregate stats for the triage manager dashboard."""
    total = count_incidents()
    open_count = count_incidents(status="open")
    critical = count_incidents(severity="Critical")
    high = count_incidents(severity="High")
    medium = count_incidents(severity="Medium")
    low = count_incidents(severity="Low")

    # Count injuries and active danger
    all_incidents = list_incidents(limit=10000)
    injury_count = sum(1 for i in all_incidents if i.get("injury_reported"))
    danger_count = sum(1 for i in all_incidents if i.get("immediate_danger"))
    sites = list({i.get("site_name", "Unknown") for i in all_incidents})

    return DashboardStats(
        total_incidents=total,
        open_incidents=open_count,
        critical_count=critical,
        high_count=high,
        medium_count=medium,
        low_count=low,
        injury_count=injury_count,
        active_danger_count=danger_count,
        sites=sorted(sites),
    )
