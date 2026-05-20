# Changelog

<!-- markdownlint-disable MD024 -- Duplicate headings are expected in changelogs for version sections -->

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added

- **NUT auto-discovery** — `NUT_AUTO_DISCOVER=true` (default) issues `LIST UPS` on startup and
  registers all reported UPS devices automatically; manual `NUT_UPS_NAME` list retained as fallback.
- **Device registry** — `DeviceRegistry` tracks all polled devices and their last-seen metadata;
  persists across restarts via `data/runtime_config.json`.
- **UPS metadata** — `PowerSnapshot` extended with `ups_model`, `ups_serial`, `ups_firmware`,
  and `ups_mfr` fields populated from NUT variable introspection.
- **Additional power events** — `device_offline`, `device_online`, `shutdown_initiated`, and
  `threshold_crossed` events added to `EventProcessor`.
- **Prometheus cardinality management** — `PROMETHEUS_DISABLE_LABELS` env var omits
  `device_id`/`device_type` labels to reduce time-series cardinality in large deployments.
- **CSV exporter** — `CsvExporter` writes snapshots to rotating CSV files with configurable
  max file size and age pruning.
- **Energy accumulator** — `EnergyAccumulator` uses trapezoidal integration for cumulative kWh
  tracking; optional cost estimation via `ENERGY_RATE_PER_KWH`.
- **SNMPv3 support** — `snmp_poller` extended with authPriv authentication using
  `SNMP_AUTH_PROTOCOL`/`SNMP_PRIV_PROTOCOL` and corresponding key variables.
- **Loki exporter** — `LokiExporter` ships structured snapshot logs to a Grafana Loki instance.
- **SQLite WAL mode, VACUUM, and indexes** — `sqlite_exporter` now opens the database in WAL
  mode, creates composite indexes for common query patterns, and runs `PRAGMA optimize` on
  startup.
- **Retention audit** — SQLite exporter enforces both `SQLITE_RETENTION_DAYS` and
  `SQLITE_MAX_ROWS` on every write cycle.
- **Grafana dashboard** — Pre-built dashboard JSON at `grafana/argus-power-monitoring.json`
  covering power/load/battery gauges, event timeline, and energy totals.
- **Multi-device polling** — Scheduler fans out to all registered NUT and SNMP devices in a
  single poll cycle.
- **Retry logic** — NUT and SNMP pollers retry transient connection failures with exponential
  backoff before marking a device offline.
- **Docker HEALTHCHECK** — API container health check wired to `/api/health`; scheduler
  container checks the health server on port 9100.
- **Multi-arch Docker build** — CI produces `linux/amd64` and `linux/arm64` images via
  `docker buildx`.
- **Environment validation** — `src/config.py` validates all required/typed env vars at import
  time and raises descriptive errors on misconfiguration.
- **Poll pause/resume** — `/api/config` `PUT` accepts `polling_paused: true/false`; scheduler
  respects the flag without restarting.
- **Alert API** — `GET /api/alerts`, `PUT /api/alerts`, and `POST /api/alerts/test` endpoints
  backed by `AlertConfigSchema` Pydantic model; supports Webhook, Gotify, ntfy, and Apprise.
- **Devices page** — React page listing all registered devices with last-seen timestamp, model,
  and status badge; includes per-device historical metric chart (`DeviceHistoryChart`).
- **Events page** — Paginated power event history with device-ID and event-type filters.
- **Alerts page** — Alert provider management UI (add/remove Webhook, Gotify, ntfy, Apprise
  providers), threshold sliders, cooldown input, and test-alert button.
- **Device history chart** — `DeviceHistoryChart` Recharts component with per-metric toggles
  and page-size selector for deep telemetry inspection.
- **Countdown timer** — Dashboard shows time until next scheduled poll with live countdown.
- **Version banner** — Settings page displays the running backend version from `/api/health`.
- **Light theme** — Full Tailwind light/dark theme toggle persisted to `localStorage`; all pages
  themed consistently.
- **Mobile layout** — Responsive nav and grid layout tested down to 375 px viewport width.

---

## [0.1.0-beta] - 2026-05-16

### Added

- **Initial architecture** — Full project scaffold mirroring Hermes design pattern, adapted for
  local-first power monitoring (UPS, PDU, sensors) via NUT and SNMP.
- **Two-process architecture** — `argus-scheduler` (APScheduler + pollers) and `argus-api`
  (FastAPI) run as separate containers sharing `argus-data` and `argus-logs` volumes.
- **NUT poller** — Polls UPS devices via raw NUT socket protocol (`LIST VAR`). Maps NUT variables
  to canonical `PowerSnapshot` fields; derives `power_watts` from nominal power × load percent
  when a direct reading is unavailable.
- **SNMP poller** — Optional pysnmp-based poller for PDUs and sensors using RFC 1628 UPS-MIB OIDs.
- **PowerSnapshot model** — Canonical telemetry unit with full validation: tz-aware timestamp,
  non-empty device ID, load/battery percent 0–100, power_watts ≥ 0.
- **Exporters** — SQLite (WAL, retention by days + row count), Prometheus (Gauges with
  device_id/device_type labels), InfluxDB (optional, `power_snapshot` measurement).
- **Event processor** — Detects `on_battery`, `power_restored`, and `battery_low` transitions
  by comparing successive snapshots per device.
- **Alert manager** — Failure-threshold alerting with cooldown, dispatched via
  `ThreadPoolExecutor`. Providers: Webhook, Gotify, ntfy, Apprise.
- **FastAPI** — REST API with API key auth, rate limiting, request-size limit middleware,
  security headers, and CORS configuration.
- **API routes** — `/api/snapshots`, `/api/events`, `/api/devices`, `/api/trigger`,
  `/api/config`, `/api/diagnostics`, `/api/health`.
- **Runtime config** — Persistent `data/runtime_config.json` with atomic writes; sentinel files
  for poll trigger and running state.
- **React 18 TypeScript frontend** — Dashboard (PowerGauge, PowerChart, EventsTable),
  Settings page, ArgusContext provider, typed API client.
- **Docker** — Multi-stage Dockerfile (Node 20 frontend build + Python 3.12-slim runtime),
  non-root `argus` user, exposes 8000/9090/9100.
- **CI pipeline** — GitHub Actions: Python lint/type-check/security/tests, frontend
  type-check/lint/build. Coverage gate ≥85%.
- **SonarQube** — `sonar-project.properties` wired for Python + TypeScript analysis with
  coverage and external issue reports.
- **Dependabot** — Weekly updates for pip, npm, and GitHub Actions dependencies.
