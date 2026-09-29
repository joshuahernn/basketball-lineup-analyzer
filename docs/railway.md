# Railway deployment

This portfolio deployment has its own project, database, and GitHub source repository.

## Services

- **Postgres:** a dedicated PostgreSQL service with a persistent volume.
- **basketball-lineup-analyzer:** the combined Angular dashboard and Django API.

Use the repository root (`/`) as the application's root directory and `Dockerfile` as its Dockerfile path. Railway builds the image using the root Dockerfile; leave the build and start command overrides empty so the image's commands are used.

The initial deployment was uploaded with the Railway CLI. GitHub autodeploys require granting the Railway GitHub app access to this private repository, then connecting the service to `joshuahernn/basketball-lineup-analyzer` on `main`.

To deploy the current local checkout again, run this from the repository root while signed into Railway:

```powershell
railway up --project 1e7166db-ee62-44e6-96e0-7ac89cee8642 --environment e8826859-6737-4a1e-a878-134bc26b4703 --service 292c10fc-e24f-479c-a57b-5822dbd128bf --detach
```

Set these application variables in Railway:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `DJANGO_SECRET_KEY` | A private, randomly generated value |
| `DJANGO_DEBUG` | `false` |
| `DJANGO_ALLOWED_HOSTS` | The app's domain plus `healthcheck.railway.app`, comma-separated |
| `PORT` | `8080` |

Generate a public HTTPS domain targeting port 8080. Set the healthcheck path to `/`, with a 120-second timeout, and restart on failure with three maximum retries. Enable Serverless to let the application sleep when idle; the first request after sleeping may take longer. The database remains persistent.

These service settings are configured in Railway. Legacy `railway.json` files are not required; Railway has deprecated that configuration format.

## Initialization and verification

The container runs `python -m scripts.prepare_deployment` before Gunicorn. It creates the database schema, applies migrations, and inserts the demo fixtures in a transaction only when all four basketball tables are empty. It does not delete or replace existing data.

Verify `/lineups-summary`, `/lineups-summary-api`, and `/api/v1/lineups?n=5` after deployment. The sample dataset contains 1,348 possessions and produces 227 five-player lineups.

Hosting uses the workspace's shared credit balance. Free-trial credit is temporary, and an always-running database can exceed the monthly free allowance. Check Railway's usage page before relying on continuous availability.
