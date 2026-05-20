# Argus

Argus is a self-hostable power monitoring application for UPS devices (via NUT),
PDUs, and sensors (via SNMP). It collects power telemetry, stores it locally in
SQLite, exposes Prometheus metrics, and sends alerts when power events occur.

## Features

- **NUT poller** — polls UPS devices via the NUT socket protocol; auto-discovers devices via `LIST UPS`
- **SNMP poller** — polls PDUs and sensors using RFC 1628 UPS-MIB OIDs; supports SNMPv1/v2c/v3 authPriv
- **SQLite storage** — WAL-mode primary datastore with configurable retention by age and row count
- **Prometheus metrics** — Gauges with `device_id`/`device_type` labels; optional cardinality management
- **InfluxDB & Loki exporters** — optional time-series and structured-log export
- **CSV exporter** — file-based exporter with size rotation and age pruning
- **Energy tracking** — trapezoidal kWh accumulation with optional cost estimation
- **Power event detection** — `on_battery`, `power_restored`, `battery_low`, `device_offline`, `device_online`, `shutdown_initiated`, `threshold_crossed`
- **Alerting** — threshold + cooldown alerting via Webhook, Gotify, ntfy, and Apprise
- **REST API** — FastAPI with API key auth, rate limiting, and security headers
- **React SPA** — Dashboard, Devices, Events, Alerts, Settings pages with light/dark theme

## Project structure

```
src/                   — Scheduler + API source
  api/                 — FastAPI application and routes
  exporters/           — SQLite, Prometheus, InfluxDB, Loki, CSV, Energy exporters
  models/              — PowerSnapshot, PowerEvent, Device dataclasses
  services/            — NUT/SNMP pollers, EventProcessor, AlertManager, HealthServer
frontend/              — React 18 TypeScript SPA (Vite, Tailwind, Recharts)
data/                  — SQLite database and runtime config (bind-mounted volume)
tests/                 — Python unit and integration tests
```

## Quick start with Docker

```bash
cp .env.example .env
# Edit .env — set NUT_HOST, API_KEY, and any alert provider URLs
docker compose up --build -d
```

- **UI + API:** <http://localhost:8000>
- **Health:** <http://localhost:8000/api/health>
- **Prometheus metrics:** <http://localhost:9090/metrics> (if enabled)
- **Scheduler health:** <http://localhost:9100/health>

## Local development

### Prerequisites

- Python 3.12+
- Node.js 20+

### Backend

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements-dev.txt
cp .env.example .env
```

Run the scheduler process:

```bash
python -m src.main
```

Run the API process (separate terminal):

```bash
uvicorn src.api.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

The Vite dev server proxies `/api/*` to `http://localhost:8000`.

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and edit as needed.

| Variable | Default | Description |
|---|---|---|
| `NUT_HOST` | `localhost` | NUT daemon host |
| `NUT_PORT` | `3493` | NUT daemon port |
| `NUT_AUTO_DISCOVER` | `true` | Auto-discover UPS devices via `LIST UPS` |
| `NUT_UPS_NAME` | `ups` | UPS name (used when auto-discovery is disabled) |
| `POLL_INTERVAL_MINUTES` | `5` | Polling interval in minutes |
| `ENABLED_EXPORTERS` | `sqlite` | Comma-separated: `sqlite,prometheus,influxdb,loki,csv,energy` |
| `SQLITE_PATH` | `data/argus.db` | SQLite database path |
| `SQLITE_RETENTION_DAYS` | `90` | Delete snapshots older than N days |
| `SQLITE_MAX_ROWS` | `100000` | Delete oldest rows when table exceeds this count |
| `PROMETHEUS_PORT` | `9090` | Prometheus metrics port |
| `PROMETHEUS_DISABLE_LABELS` | `false` | Set `true` to omit `device_id`/`device_type` labels |
| `ENERGY_RATE_PER_KWH` | `0` | Cost per kWh (0 = disable cost estimation) |
| `API_KEY` | _(empty)_ | API key (min 32 chars); leave empty to disable auth |
| `ALLOWED_ORIGINS` | `http://localhost:3000,...` | CORS allowed origins |
| `ALERT_FAILURE_THRESHOLD` | `3` | Consecutive failures before alerting |
| `ALERT_COOLDOWN_SECONDS` | `3600` | Minimum seconds between repeated alerts |
| `WEBHOOK_URL` | _(empty)_ | Webhook alert provider URL |
| `GOTIFY_URL` / `GOTIFY_TOKEN` | _(empty)_ | Gotify alert provider |
| `NTFY_URL` / `NTFY_TOPIC` | _(empty)_ | ntfy alert provider |
| `APPRISE_URL` | _(empty)_ | Apprise alert provider URL |
| `HEALTH_PORT` | `9100` | Scheduler health server port |

See `.env.example` for the full list including SNMP, SNMPv3, InfluxDB, Loki, CSV, and event threshold settings.

## API endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | — | Scheduler and exporter health |
| `GET` | `/api/snapshots` | — | Paginated telemetry history |
| `GET` | `/api/events` | — | Paginated power event history |
| `GET` | `/api/devices` | — | Registered device list |
| `GET/PUT` | `/api/config` | ✓ | Poll interval and enabled exporters |
| `GET/PUT` | `/api/devices` | ✓ | Add/remove monitored devices |
| `GET/PUT` | `/api/alerts` | ✓ | Alert provider configuration |
| `POST` | `/api/alerts/test` | ✓ | Dispatch a test alert |
| `POST` | `/api/trigger` | ✓ | Manual poll trigger |
| `GET` | `/api/trigger/status` | — | Last trigger status |
| `GET` | `/api/diagnostics` | — | Last snapshot and events |
| `GET` | `/api/energy` | — | Cumulative energy and cost |

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

Coverage gate: ≥85% (enforced in CI).

## Grafana

A pre-built Grafana dashboard is available at `grafana/argus-power-monitoring.json`.
Import it via **Dashboards → Import** in your Grafana instance and point the
Prometheus data source at `http://localhost:9090`.

## Open source

- MIT License (`LICENSE`)
- Contribution guide (`CONTRIBUTING.md`)
- Security policy (`SECURITY.md`)
- Code of conduct (`CODE_OF_CONDUCT.md`)
