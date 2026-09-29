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
| Deployment configuration | Railway, Gunicorn, Express |

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

The 12 unit tests cover derived metrics, including zero-denominator handling. They do not constitute full end-to-end coverage of every aggregation and UI interaction.

## Deploy your own instance

Create a new PostgreSQL service and separate backend/frontend services. Use `/backend` and `/frontend` as their respective root directories. The checked-in `railway.json` files define build and start commands; connect the backend to the new database using `DATABASE_URL` and initialize the `app` schema before migrations.

Set `BACKEND_PUBLIC_DOMAIN` in `frontend/src/environments/environment.prod.ts` to your new backend's HTTPS origin, without a trailing slash, before building. Its empty default supports a same-origin reverse proxy forwarding `/api/v1` to Django. No existing deployment is linked or configured in this repository.

Import the demo data into that new database, set appropriate production host/CORS restrictions, and keep credentials out of Git.
