# Local development

Prerequisites: Python 3.12 or 3.13, Node.js 22, npm, and PostgreSQL. Commands below use PowerShell from the repository root. To try the hosted application without installing anything, open the [live demo](https://basketball-lineup-analyzer-production.up.railway.app/lineups-summary).

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

Database defaults are `basketball`, `basketball_app`, `127.0.0.1`, and port `5432`. Override them through `PGDATABASE`, `PGUSER`, `PGHOST`, and `PGPORT`, or provide `DATABASE_URL`. Set `DJANGO_SECRET_KEY` to a private value and `DJANGO_DEBUG=false` when deploying. The [`.env.example`](../.env.example) file documents the variables; Django does not load it automatically.

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

For deployment configuration, see [Railway deployment settings](railway.md).
