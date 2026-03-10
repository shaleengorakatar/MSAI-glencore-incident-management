# Glencore Mining Incident Management – Backend API

AI-powered H&S incident logging and triage system for mining operations.

## Features

- **Incident Submission** – Workers log incidents with text + photo upload
- **AI Text Analysis** – Auto-categorize, score severity/priority, extract entities, suggest actions
- **AI Photo Analysis** – GPT-4o vision detects hazards in incident photos
- **Triage Dashboard** – Managers see AI-prioritized incident queue with stats
- **Thematic View** – Incidents grouped by safety themes with drill-down
- **Similar Incidents** – Keyword-based matching to surface repeat patterns
- **25 Seed Incidents** – Realistic mining H&S demo data pre-loaded

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 4. Run the server
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/incidents` | Submit incident (multipart form + photo) |
| `GET` | `/api/incidents` | List incidents (filterable) |
| `GET` | `/api/incidents/{id}` | Get incident detail |
| `PATCH` | `/api/incidents/{id}` | Update status/assignment |
| `GET` | `/api/incidents/{id}/similar` | Get similar incidents |
| `GET` | `/api/themes` | Thematic overview for managers |
| `GET` | `/api/themes/{name}/incidents` | Drill-down into a theme |
| `GET` | `/api/dashboard/stats` | Aggregate dashboard stats |
| `GET` | `/health` | Health check |

## API Docs

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Tech Stack

- **FastAPI** – async Python API framework
- **SQLite** – zero-config database
- **OpenAI GPT-4o** – text analysis + vision
- **Pydantic v2** – request/response validation
