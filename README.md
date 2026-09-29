# Basketball Lineup Analyzer

A full-stack basketball analytics application for exploring lineup performance, comparing teams, and understanding how teams perform with individual players on the court. Built with **Angular, Django REST Framework, and PostgreSQL**.

## Features

- Aggregate offensive and defensive possession statistics for every observed 1–5-player combination.
- Filter results by team and game; view rosters and highlight players who participated.
- Compare team offensive, defensive, and net ratings with interactive charts.
- Explore shooting efficiency, rebounding, turnovers, play style, tempo, and fourth-quarter performance.
- Rank on-court player performance by net rating.
- Recommend five-player lineups for scoring, rebounding, and overall performance. Rebounding ties use net rating.
- Inspect the JSON API through the built-in API Explorer.

## Architecture

The Angular dashboard requests data from Django REST endpoints. The backend queries PostgreSQL possessions, groups player combinations, accumulates statistics, and calculates derived metrics. Team summaries aggregate possessions directly rather than averaging lineup ratings.

| Component | Technology |
| --- | --- |
| Dashboard and charts | Angular, TypeScript, Angular Material, AG Charts |
| API and analytics | Python, Django, Django REST Framework |
| Storage | PostgreSQL |
| Deployment | Railway, Docker, Gunicorn, WhiteNoise |

## Demo dataset

The included fixture data has 1,348 possessions, 60 player records, three fictional teams, and seven games. It produces 227 observed five-player lineups; 48 players appear in the possession data. This is a demonstration dataset, not official league data.

The portfolio application builds on existing Angular/Django scaffolding and supplied fixture data. The analytics, filtering, comparisons, and recommendations are the focus of this version. Third-party dependency notices are retained. See [analysis notes](docs/analysis.md) for methodology and example results.

## Run locally

Prerequisites: Python 3.12 or 3.13, Node.js 22, npm, and PostgreSQL. Commands below use PowerShell from the repository root.

### 1. Create a dedicated database

In `psql`, connected as a PostgreSQL administrator:

```sql
CREATE ROLE basketball_app LOGIN CREATEDB;
\password basketball_app
CREATE DATABASE basketball OWNER basketball_app;
\connect basketball
CREATE SCHEMA app AUTHORIZATION basketball_app;
```

Choose your own local database password at the prompt. This app uses its own database and does not require another project's database or deployment.

### 2. Install and start the backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
$env:PGPASSWORD = 'your-local-database-password'
cd backend
python manage.py migrate
$env:PYTHONPATH = '.'
python scripts/ingest_raw_data.py
python manage.py runserver
```

The API runs at `http://127.0.0.1:8000/api/v1`. The ingestion script replaces the basketball fixture tables in the configured database; run it against the dedicated demo database above.

Database defaults are `basketball`, `basketball_app`, `127.0.0.1`, and port `5432`. Override them through `PGDATABASE`, `PGUSER`, `PGHOST`, and `PGPORT`, or provide `DATABASE_URL`. Set `DJANGO_SECRET_KEY` to a private value and `DJANGO_DEBUG=false` when deploying. The `.env.example` file documents the variables; Django does not load it automatically.

### 3. Start the frontend

In another terminal:

```powershell
cd frontend
npm ci
npm start
```

Open `http://localhost:4200`. Use **Dashboard** for the interface and **API Explorer** for the raw results.

## API

| Endpoint | Parameters |
| --- | --- |
| `/api/v1/lineups` | `n` (1–5; default 5), optional `team_id`, optional `game_id` |
| `/api/v1/team-games` | `team_id` |
| `/api/v1/team-summary` | `team_id`, optional `game_id` |
| `/api/v1/player-impact` | None; league-wide results |

Team and game IDs are UUIDs from the fixture data and API responses.

## Validation

```powershell
# From backend, with the virtual environment active:
python manage.py test app.tests

# From frontend:
npm run build
```

The 15 unit tests cover derived metrics, including zero-denominator handling, and dashboard routing. They do not constitute full end-to-end coverage of every aggregation and UI interaction.

## Deploy your own instance

The root `Dockerfile` builds Angular and serves its compiled files alongside the Django API. This uses two Railway services: one application and one dedicated PostgreSQL database. Both the UI and API share an origin, so `BACKEND_PUBLIC_DOMAIN` stays empty in the production frontend configuration.

On startup, the app creates the `app` schema, applies migrations, and imports the demo fixtures only if all four basketball tables are empty. Existing data is retained on redeployment. Set `DATABASE_URL`, a private `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, and `DJANGO_ALLOWED_HOSTS` in Railway.

See [Railway deployment settings](docs/railway.md) for the service configuration. Credentials belong in service variables, never in Git.
