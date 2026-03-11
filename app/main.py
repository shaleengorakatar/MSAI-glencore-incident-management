"""
Glencore Mining Incident Management – FastAPI Backend
AI-powered H&S incident logging and triage for mine operations.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import ai_utils, dashboard, incidents, themes
from app.services.seed_data import seed_demo_data

app = FastAPI(
    title="Glencore Incident Management API",
    description=(
        "AI-powered mining H&S incident logging and triage. "
        "Workers log incidents with text + photos; AI structures, scores, "
        "and categorizes them. Triage managers get a prioritized queue "
        "with thematic views and drill-down."
    ),
    version="1.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS – allow requests from Lovable frontend and local dev
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *settings.cors_origin_list,
    ],
    allow_origin_regex=r"https://.*\.(lovable\.app|lovableproject\.com)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Serve uploaded photos
# ---------------------------------------------------------------------------
# upload_dir is already created in config.py, but ensure it's a string for StaticFiles
app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(incidents.router, prefix="/api")
app.include_router(themes.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(ai_utils.router, prefix="/api")


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    init_db()
    seed_demo_data()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "glencore-incident-management-api",
        "version": "1.0.1",
        "ai_routes_available": True,
    }
