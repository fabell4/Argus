# Changelog

<!-- markdownlint-disable MD024 -- Duplicate headings are expected in changelogs for version sections -->

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

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
