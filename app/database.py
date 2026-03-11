from __future__ import annotations

import sqlite3
import json
import os
from contextlib import contextmanager

from app.config import settings

DB_PATH = settings.database_url.replace("sqlite:///", "")


def get_db_path() -> str:
    return DB_PATH


def init_db():
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                reporter_name TEXT NOT NULL,
                site_name TEXT NOT NULL,
                location TEXT,
                reported_at TEXT NOT NULL,
                short_description TEXT,
                detailed_description TEXT,
                people_impacted INTEGER DEFAULT 0,
                injury_reported INTEGER DEFAULT 0,
                immediate_danger INTEGER DEFAULT 0,
                photo_filename TEXT,
                status TEXT DEFAULT 'open',

                -- AI-generated fields
                ai_title TEXT,
                ai_summary TEXT,
                ai_categories TEXT,          -- JSON array
                ai_severity TEXT,
                ai_priority TEXT,
                ai_confidence REAL,
                ai_severity_rationale TEXT,
                ai_recommended_actions TEXT,  -- JSON array
                ai_root_causes TEXT,          -- JSON array
                ai_photo_analysis TEXT,
                ai_extracted_entities TEXT,   -- JSON object
                ai_themes TEXT,               -- JSON array

                -- Management fields
                assigned_to TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
            CREATE INDEX IF NOT EXISTS idx_incidents_ai_severity ON incidents(ai_severity);
            CREATE INDEX IF NOT EXISTS idx_incidents_ai_priority ON incidents(ai_priority);
            CREATE INDEX IF NOT EXISTS idx_incidents_site_name ON incidents(site_name);
            CREATE INDEX IF NOT EXISTS idx_incidents_reported_at ON incidents(reported_at);
        """)


@contextmanager
def _connect():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_incident(data: dict) -> dict:
    """Insert a new incident and return the full row."""
    # Serialize JSON fields
    for key in ("ai_categories", "ai_recommended_actions", "ai_root_causes", "ai_themes"):
        if key in data and isinstance(data[key], (list, dict)):
            data[key] = json.dumps(data[key])
    if "ai_extracted_entities" in data and isinstance(data["ai_extracted_entities"], dict):
        data["ai_extracted_entities"] = json.dumps(data["ai_extracted_entities"])

    cols = ", ".join(data.keys())
    placeholders = ", ".join(f":{k}" for k in data.keys())
    with _connect() as conn:
        conn.execute(f"INSERT INTO incidents ({cols}) VALUES ({placeholders})", data)
    return get_incident(data["id"])


def update_incident(incident_id: str, data: dict) -> dict | None:
    for key in ("ai_categories", "ai_recommended_actions", "ai_root_causes", "ai_themes"):
        if key in data and isinstance(data[key], (list, dict)):
            data[key] = json.dumps(data[key])
    if "ai_extracted_entities" in data and isinstance(data["ai_extracted_entities"], dict):
        data["ai_extracted_entities"] = json.dumps(data["ai_extracted_entities"])

    sets = ", ".join(f"{k} = :{k}" for k in data.keys())
    data["_id"] = incident_id
    with _connect() as conn:
        conn.execute(f"UPDATE incidents SET {sets}, updated_at = datetime('now') WHERE id = :_id", data)
    return get_incident(incident_id)


def get_incident(incident_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def list_incidents(
    status: str | None = None,
    severity: str | None = None,
    priority: str | None = None,
    site: str | None = None,
    limit: int = 100,
    offset: int = 0,
    reporter_name: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM incidents WHERE 1=1"
    params: dict = {}
    if status:
        query += " AND status = :status"
        params["status"] = status
    if severity:
        query += " AND ai_severity = :severity"
        params["severity"] = severity
    if priority:
        query += " AND ai_priority = :priority"
        params["priority"] = priority
    if site:
        query += " AND site_name = :site"
        params["site"] = site
    if reporter_name:
        query += " AND reporter_name = :reporter_name"
        params["reporter_name"] = reporter_name

    query += " ORDER BY CASE ai_priority WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 WHEN 'P3' THEN 3 WHEN 'P4' THEN 4 ELSE 5 END, reported_at DESC"
    query += " LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def count_incidents(
    status: str | None = None,
    severity: str | None = None,
    priority: str | None = None,
    site: str | None = None,
    reporter_name: str | None = None,
) -> int:
    query = "SELECT COUNT(*) FROM incidents WHERE 1=1"
    params: dict = {}
    if status:
        query += " AND status = :status"
        params["status"] = status
    if severity:
        query += " AND ai_severity = :severity"
        params["severity"] = severity
    if priority:
        query += " AND ai_priority = :priority"
        params["priority"] = priority
    if site:
        query += " AND site_name = :site"
        params["site"] = site
    if reporter_name:
        query += " AND reporter_name = :reporter_name"
        params["reporter_name"] = reporter_name

    with _connect() as conn:
        return conn.execute(query, params).fetchone()[0]


def get_themes_summary() -> list[dict]:
    """Return incident counts grouped by AI theme for the thematic dashboard."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, ai_themes, ai_severity, ai_priority, ai_title, site_name, status, reported_at FROM incidents ORDER BY reported_at DESC"
        ).fetchall()

    theme_map: dict[str, dict] = {}
    for row in rows:
        row_dict = dict(row)
        themes_raw = row_dict.get("ai_themes")
        if not themes_raw:
            continue
        try:
            themes = json.loads(themes_raw)
        except (json.JSONDecodeError, TypeError):
            continue
        for theme in themes:
            if theme not in theme_map:
                theme_map[theme] = {
                    "theme": theme,
                    "total_count": 0,
                    "severity_breakdown": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
                    "open_count": 0,
                    "sites_affected": set(),
                    "recent_incidents": [],
                }
            bucket = theme_map[theme]
            bucket["total_count"] += 1
            sev = row_dict.get("ai_severity", "Low")
            if sev in bucket["severity_breakdown"]:
                bucket["severity_breakdown"][sev] += 1
            if row_dict.get("status") == "open":
                bucket["open_count"] += 1
            bucket["sites_affected"].add(row_dict.get("site_name", "Unknown"))
            if len(bucket["recent_incidents"]) < 5:
                bucket["recent_incidents"].append({
                    "id": row_dict["id"],
                    "title": row_dict.get("ai_title"),
                    "severity": sev,
                    "priority": row_dict.get("ai_priority"),
                    "site": row_dict.get("site_name"),
                    "reported_at": row_dict.get("reported_at"),
                    "status": row_dict.get("status"),
                })

    results = []
    for theme_data in theme_map.values():
        theme_data["sites_affected"] = list(theme_data["sites_affected"])
        results.append(theme_data)

    # Sort by total_count descending
    results.sort(key=lambda x: x["total_count"], reverse=True)
    return results


def get_incidents_by_theme(theme: str) -> list[dict]:
    """Return all incidents that have a specific theme."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM incidents WHERE ai_themes LIKE ? ORDER BY "
            "CASE ai_priority WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 WHEN 'P3' THEN 3 WHEN 'P4' THEN 4 ELSE 5 END, reported_at DESC",
            (f'%"{theme}"%',),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def search_similar_text(text: str, exclude_id: str | None = None, limit: int = 5) -> list[dict]:
    """Simple keyword-based similarity search over incident descriptions."""
    words = [w.lower() for w in text.split() if len(w) > 3]
    if not words:
        return []

    query = "SELECT * FROM incidents WHERE ("
    conditions = []
    params = {}
    for i, word in enumerate(words[:10]):
        key = f"w{i}"
        conditions.append(f"(LOWER(short_description) LIKE :{key} OR LOWER(detailed_description) LIKE :{key} OR LOWER(ai_title) LIKE :{key})")
        params[key] = f"%{word}%"
    query += " OR ".join(conditions) + ")"

    if exclude_id:
        query += " AND id != :exclude_id"
        params["exclude_id"] = exclude_id

    query += " LIMIT :limit"
    params["limit"] = limit

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    # Parse JSON fields back
    for key in ("ai_categories", "ai_recommended_actions", "ai_root_causes", "ai_themes"):
        if d.get(key):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                pass
    if d.get("ai_extracted_entities"):
        try:
            d["ai_extracted_entities"] = json.loads(d["ai_extracted_entities"])
        except (json.JSONDecodeError, TypeError):
            pass
    # Convert boolean ints
    for key in ("injury_reported", "immediate_danger"):
        if key in d:
            d[key] = bool(d[key])
    return d
