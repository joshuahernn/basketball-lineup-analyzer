# Basketball Lineup Analyzer

A full-stack basketball analytics application for exploring lineup performance, comparing teams, and understanding how teams perform with individual players on the court. Built with **Angular, Django REST Framework, and PostgreSQL**, and hosted on **Railway**.

**[Open the live demo](https://basketball-lineup-analyzer-production.up.railway.app/lineups-summary)** · [API Explorer](https://basketball-lineup-analyzer-production.up.railway.app/lineups-summary-api)

## Try the demo

No installation or account is required. Choose a team to explore its ratings, roster, and recommended lineups. Filter by game or compare teams to see how their performance changes.

The app may take a moment to wake up after being idle.

## Features

- Analyze every observed 1–5-player combination using offensive and defensive possession statistics.
- Filter by team and game, view rosters, and highlight players who participated.
- Compare offensive, defensive, and net ratings with interactive charts.
- Explore shooting efficiency, rebounding, turnovers, play style, tempo, and fourth-quarter performance.
- Rank player on-court performance by net rating.
- Recommend five-player lineups for scoring, rebounding, and overall performance, with net rating breaking rebounding ties.
- Explore the underlying JSON results through the API Explorer.

## How it works

The Angular dashboard requests data from Django REST endpoints. The backend queries PostgreSQL possessions, groups player combinations, accumulates statistics, and calculates derived metrics. Team summaries aggregate possessions directly rather than averaging lineup ratings.

| Component | Technology |
| --- | --- |
| Dashboard and charts | Angular, TypeScript, Angular Material, AG Charts |
| API and analytics | Python, Django, Django REST Framework |
| Storage | PostgreSQL |
| Hosting | Railway, Docker, Gunicorn, WhiteNoise |

The Railway deployment serves the dashboard and API together, with a separate PostgreSQL database.

## Demo data and methodology

The included dataset contains **1,348 possessions**, **60 player records**, **three fictional teams**, and **seven games**. It produces **227 observed five-player lineups**; **48 players** appear in the possession data. This is demonstration data, not official league data.

The application builds on existing Angular/Django scaffolding and supplied fixture data. The analytics, filtering, comparisons, and recommendations are the focus of this version. Third-party dependency notices are retained.

See the [analysis notes](docs/analysis.md) for metric definitions, sample-size limitations, and example results.

## Development

The project includes 15 unit tests covering derived metrics, zero-denominator handling, and dashboard routing.

- [Local setup and test commands](docs/development.md)
- [Railway deployment settings](docs/railway.md)
