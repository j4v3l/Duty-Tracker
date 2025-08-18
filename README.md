# Duty Tracker

A military duty assignment tracking system built with FastAPI, Alpine.js, and TailwindCSS.

## Features

- Track personnel assignments to various duty posts
- Monitor fairness in duty distribution
- Manage different types of posts (SOG, CQ, ECP, VCP, ROVER, Stand by)
- Equipment requirements tracking
- Interactive web interface

## Setup

1. Install dependencies:
```bash
uv sync --group dev
```

2. Run the development server:
```bash
uv run uvicorn app.main:app --reload
```

3. Open your browser to `http://localhost:8000`

## Project Structure

```
duty-tracker/
├── app/
│   ├── main.py          # FastAPI application
│   ├── models.py        # Database models
│   ├── schemas.py       # Pydantic schemas
│   ├── crud.py          # Database operations
│   ├── database.py      # Database setup
│   └── routers/         # API routes
├── static/
│   ├── css/            # TailwindCSS styles
│   └── js/             # Alpine.js components
├── templates/          # Jinja2 templates
└── tests/              # Test files
```

## API Endpoints

- `GET /` - Main dashboard
- `GET /api/personnel` - List all personnel
- `GET /api/posts` - List all posts
- `GET /api/assignments` - List assignments
- `POST /api/assignments` - Create new assignment
- `GET /api/fairness` - Get fairness statistics
