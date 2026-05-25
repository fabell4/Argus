# Argus

Argus is a self-hostable power use reporting platform with:

- **Backend:** Python (FastAPI)
- **Frontend:** React (Vite)
- **Deployment:** Docker images via Docker Compose

## Project structure

- `src/` — FastAPI scheduler and API service
- `frontend/` — React UI
- `docker-compose.yml` — self-hosted deployment

## Local development

### Backend

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
export ALLOWED_ORIGINS=http://localhost:5173
# Start the scheduler process
python -m src.main
# Start the API process (separate terminal)
uvicorn src.api.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

The Vite dev server proxies `/api/*` to `http://localhost:8000`.

## Running tests

### Python (346 tests, ≥90% coverage)

```bash
pytest --cov=src --cov-report=term-missing -q
```

### Frontend (108 tests, ≥70% coverage)

```bash
cd frontend
npm run test:coverage
```

## Environment variables

Copy `.env.example` to `.env` and adjust as needed. Key variables:

| Variable | Default | Description |
| --- | --- | --- |
| `NUT_HOST` | `localhost` | NUT daemon hostname |
| `NUT_PORT` | `3493` | NUT daemon port |
| `NUT_UPS_NAME` | `ups` | UPS name (if `NUT_AUTO_DISCOVER=false`) |
| `NUT_AUTO_DISCOVER` | `true` | Auto-discover all UPS devices via `LIST UPS` |
| `POLL_INTERVAL_MINUTES` | `5` | Polling interval |
| `ENABLED_EXPORTERS` | `sqlite` | Comma-separated: `sqlite`, `prometheus`, `influxdb`, `loki`, `csv`, `energy` |
| `SQLITE_PATH` | `data/argus.db` | SQLite database path |
| `API_KEY` | `` | API key (min 32 chars, leave empty to disable auth) |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:5173` | CORS allowed origins |

See `.env.example` for the full list of supported variables.

## API

Interactive docs available at <http://localhost:8000/api/docs>.

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/health` | GET | Scheduler status and last poll time |
| `/api/snapshots` | GET | Paginated power snapshot history |
| `/api/events` | GET | Paginated power event history |
| `/api/devices` | GET/POST/PUT/DELETE | Device registry |
| `/api/config` | GET/PUT | Poll interval and exporter config |
| `/api/trigger` | POST | Manual poll trigger |
| `/api/trigger/status` | GET | Current poll trigger status |
| `/api/diagnostics` | GET | Last snapshot and events from shared state |
| `/api/alerts` | GET/PUT | Alert provider configuration |
| `/api/alerts/test` | POST | Send a test alert |
| `/api/energy` | GET | Cumulative energy (kWh) and cost estimate |

## Self-hosting with Docker

```bash
docker compose up --build -d
```

- App (API + frontend): <http://localhost:8000>
- API health: <http://localhost:8000/api/health>

The backend CORS policy is configured with `ALLOWED_ORIGINS` (comma-separated).

## Open source best practices

- MIT License (`LICENSE`)
- Contribution guide (`CONTRIBUTING.md`)
- Security policy (`SECURITY.md`)
- Code of conduct (`CODE_OF_CONDUCT.md`)
