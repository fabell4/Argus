# Argus — Roadmap & TODO

---

## ✅ Completed (v0.1.0-beta)

### Foundation

- [x] `PowerSnapshot` — canonical telemetry model with full validation (tz-aware timestamp,
  device ID, load/battery 0–100, power_watts ≥ 0)
- [x] `PowerEvent` — structured event model with type, device ID, timestamp, and metadata
- [x] `Device` — device descriptor model (id, type, host, poller type)
- [x] `NUTPoller` — polls UPS devices via raw NUT socket (`LIST VAR`); derives `power_watts`
  from nominal power × load when direct reading unavailable
- [x] `SNMPPoller` — optional pysnmp-based poller for PDUs and sensors using RFC 1628 UPS-MIB OIDs
- [x] `BaseExporter` — interface contract for all exporters
- [x] `SnapshotDispatcher` — fan-out hub with `DispatchError` aggregation
- [x] `SQLiteExporter` — WAL-mode primary store with retention by age (days) and row count
- [x] `PrometheusExporter` — Gauges with `device_id`/`device_type` labels
- [x] `InfluxDBExporter` — optional time-series exporter (`power_snapshot` measurement)
- [x] `EventProcessor` — detects `on_battery`, `power_restored`, `battery_low` transitions
  between consecutive snapshots per device
- [x] `AlertManager` — failure-threshold alerting with cooldown, async dispatch via
  `ThreadPoolExecutor`; providers: Webhook, Gotify, ntfy, Apprise
- [x] `HealthServer` — lightweight HTTP server returning scheduler status and last poll timestamp
- [x] `RuntimeConfig` — JSON persistence with atomic writes; sentinel files for poll trigger
  and running state
- [x] `SharedState` — thread-safe dataclass for diagnostics and alert manager reference
- [x] `ExporterRegistry` — maps exporter names to factory functions

### API

- [x] FastAPI application with API key auth, rate limiting, request-size limit middleware,
  security headers, and CORS configuration
- [x] `GET/POST /api/config` — poll interval and enabled exporters
- [x] `GET /api/snapshots` — paginated telemetry history
- [x] `GET /api/events` — paginated power event history
- [x] `GET /api/devices` — registered device list
- [x] `POST /api/trigger` — manual poll trigger; `GET /api/trigger/status`
- [x] `GET /api/diagnostics` — last snapshot and events from shared state
- [x] `GET /api/health` — scheduler and exporter health

### Frontend

- [x] React 18 + TypeScript + Vite scaffold with Tailwind CSS dark theme
- [x] `ArgusContext` provider with typed API client
- [x] Dashboard page — `PowerGauge`, `PowerChart`, `EventsTable` components
- [x] Settings page — poll interval and exporter toggles
- [x] `Layout` — nav, responsive shell

### Infrastructure

- [x] Multi-stage Dockerfile (Node 20 frontend build + Python 3.12-slim runtime), non-root user
- [x] `docker-compose.yml` — two-process (scheduler + API) with shared `argus-data` volume
- [x] CI pipeline — ruff, mypy, bandit, semgrep, pytest (≥85% coverage gate); frontend
  tsc/ESLint/Vitest; Safety, pip-audit, Trivy, npm-audit supply-chain scans
- [x] SonarQube — `sonar-project.properties` for Python + TypeScript analysis
- [x] Dependabot — weekly updates for pip, npm, and GitHub Actions
- [x] `constants.py` — `DeviceType`, `PollerType`, `ExporterType`, `AlertProviderType`,
  `EventType`, `UPSStatus` as `StrEnum`

### Static Analysis (resolved in beta)

- [x] Mypy clean — 0 errors in 36 source files (Protocol typing for optional InfluxDB client)
- [x] Ruff clean — encoding, unused imports, global statements, logging.exception, noqa
- [x] ESLint/TypeScript clean — tsc --noEmit passes; Vite build clean

---

## Phase 1 — Stability ✅

_Goal: make the deployed instance reliable before adding features. Required before alpha tag._

- [x] Retry logic in `NUTPoller` and `SNMPPoller` — one retry on transient socket/SNMP failure
  to handle first-run hangs and brief network blips
- [x] Docker `HEALTHCHECK` — point to `GET /api/health` once verified stable
- [x] Multi-architecture Docker build — add `linux/arm64` target for Raspberry Pi / ARM servers
  (common UPS monitoring hardware)
- [x] Environment validation on startup — warn on scheduler start if a configured alert provider
  URL is unreachable; log clearly rather than failing silently
- [x] Pause/resume polling toggle — runtime flag to pause/resume the scheduler without
  restarting the container; expose via `PUT /api/config` and a UI button (default: enabled)
- [x] Loki exporter — ship `PowerSnapshot` and `PowerEvent` records as structured log lines to
  a Loki push endpoint; mirrors Hermes's `LokiExporter` pattern adapted for power telemetry

> 🏁 **Alpha release gate** — all Phase 1 items must be complete before tagging an alpha release.

---

## Phase 2 — Data & Observability

_Goal: make historical data more useful and integrate with the wider observability stack._

- [x] SQLite WAL checkpoint management — run `PRAGMA wal_checkpoint(TRUNCATE)` after each
  retention prune to keep WAL file bounded; mirrors Hermes v1.1 pattern
- [x] SQLite VACUUM automation — check `PRAGMA freelist_count` post-prune; issue `VACUUM` when
  fragmentation exceeds 20% of total page count
- [x] SQLite timestamp index — `CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON
  power_snapshots(timestamp)` and equivalent on `power_events`; gives 10–100× faster
  date-range queries as history grows
- [x] Data retention enforcement audit — verify `SQLITE_RETENTION_DAYS` and `SQLITE_MAX_ROWS`
  prune runs correctly on schedule; add integration test
- [x] Grafana dashboard JSON — pre-built power monitoring dashboard for one-click import
  (UPS status timeline, battery %, load %, input/output voltage, runtime remaining, event log)
- [x] Multi-device polling — poll multiple NUT and SNMP devices per cycle; aggregate into a
  single dispatch pass; `DEVICES` env var as JSON or the runtime_config device list
- [x] NUT `LIST UPS` auto-discovery — on startup, issue `LIST UPS` to enumerate all UPS
  devices served by the NUT daemon; auto-register discovered devices rather than requiring
  explicit `NUT_UPS_NAME` config; manual override still supported
- [x] Device registry in runtime config — add/remove monitored devices via
  `PUT /api/devices` without restarting; persisted in `data/runtime_config.json`
- [x] UPS model/firmware metadata — capture `ups.model`, `ups.firmware`, `ups.serial`,
  and `ups.mfr` from NUT `LIST VAR`; store in the device registry and expose via
  `GET /api/devices`; useful for inventory and dashboard display
- [x] Additional event detection — implement remaining `EventType` variants:
  `DEVICE_OFFLINE` / `DEVICE_ONLINE` (missed poll threshold), `SHUTDOWN_INITIATED`
  (battery below critical floor), `THRESHOLD_CROSSED` (configurable metric thresholds)
- [x] Prometheus label cardinality management — `PROMETHEUS_DISABLE_LABELS=true` env var makes
  `device_id`/`device_type` labels optional to prevent unbounded time series growth in large
  multi-device deployments
- [x] `CSVExporter` — optional file-based exporter; appends one row per snapshot to a rotating
  CSV file (`CSV_PATH`, `CSV_MAX_SIZE_MB`, `CSV_RETENTION_DAYS`); useful for simple log
  ingestion into external tools without a database dependency; mirrors Hermes's `CSVExporter`
  pattern adapted for `PowerSnapshot` fields
- [x] Energy accumulation (kWh tracking) — accumulate watt-hours between poll cycles using
  trapezoidal integration (`power_watts × Δt`); store cumulative `energy_wh` in SQLite;
  expose `argus_energy_kwh_total` Prometheus counter; optional cost estimation via
  `ENERGY_RATE_PER_KWH` env var and `GET /api/energy` endpoint
- [x] SNMPv3 authentication and encryption — extend `SNMPPoller` to support SNMPv3 `authPriv`
  mode (`SNMP_V3_USERNAME`, `SNMP_V3_AUTH_PROTOCOL`, `SNMP_V3_AUTH_KEY`,
  `SNMP_V3_PRIV_PROTOCOL`, `SNMP_V3_PRIV_KEY`); required for security-conscious production
  deployments; v1/v2c community strings remain default

> 🏁 **Alpha → Beta release gate** — all Phase 1–2 items must be complete before tagging beta.

---

## Phase 3 — UI & UX Improvements

_Goal: complete the React frontend with full Argus-specific pages and interactions._

- [x] Devices page — list all monitored devices with current status indicator (online/on battery
  /offline), live metrics summary cards, and last-seen timestamp
- [x] Events page — full paginated power event history; filter by device, event type, and date
  range; colour-coded severity (on-battery = amber, battery-low = red, restored = green)
- [x] Alert configuration page — UI for configuring alert providers (webhook URL, Gotify token,
  ntfy topic, Apprise URL) backed by `GET/PUT /api/alerts`; send-test button
- [x] Alert API endpoints — `GET /api/alerts` and `PUT /api/alerts` with authentication;
  mirrors Hermes alert API pattern
- [x] Historical chart per device — multi-device power history chart (Recharts); device selector
  dropdown; metrics selector (battery %, load %, power W, voltage, runtime remaining)
- [x] Countdown timer and manual trigger — next-poll countdown and "Poll Now" button on
  Dashboard; mirrors Hermes UI pattern
- [x] Version banner — display running version; poll GitHub API for latest release and show
  update notification when behind
- [x] Light theme toggle — light / dark mode switch persisted in localStorage
- [x] Mobile-responsive layout improvements — ensure all pages render correctly on narrow screens

> 🏁 **Beta → Full release gate** — all Phase 1–3 items must be complete before tagging v1.0.

---

## Phase 4 — Alerting & Quality Assurance

_Goal: harden alerting for power-specific events and complete pre-release code reviews._

### Power-Aware Alerting

- [x] Power event alerting — fire alert notifications on `ON_BATTERY`, `BATTERY_LOW`, and
  `DEVICE_OFFLINE` events (not just consecutive poll failures); configurable per event type
- [x] Alert severity levels — LOW / MEDIUM / HIGH / CRITICAL mapped to event types;
  allow per-provider severity filter
- [x] Alert recovery notifications — send "power restored" and "device online" notifications
  when a device recovers; configurable cooldown per device
- [x] Alert test cooldown — enforce a minimum 10-second cooldown between test-alert requests
  from the UI to prevent provider rate-limit exhaustion

### Quality Assurance

- [x] Comprehensive test suite expansion — target ≥200 Python tests covering:
  - `NUTPoller` (mock socket: happy path, auth, retry, parse errors)
  - `SNMPPoller` (mock pysnmp: happy path, timeout, import missing, SNMPv3 auth/priv)
  - `SQLiteExporter` (schema, write, prune by age, prune by row count, WAL checkpoint, timestamp index)
  - `CSVExporter` (file creation, append, rotation by size, prune by age, missing directory)
  - `EnergyAccumulator` (watt-hour calculation, cumulative storage, cost estimation)
  - `PrometheusExporter` (gauge values, counter reset, label presence, cardinality flag)
  - `InfluxDBExporter` (payload shape, optional import guard)
  - `LokiExporter` (payload shape, URL validation, retry)
  - `EventProcessor` (all event types, first-run no-previous, multi-device)
  - `AlertManager` (threshold, cooldown, async dispatch, recovery)
  - Alert providers (URL validation, HTTPS enforcement, timeout, error propagation)
  - API routes (auth, rate limit, request size, SSRF, all endpoints)
  - `RuntimeConfig` (validation, cache behavior, atomic write, edge cases)
  - `SnapshotDispatcher` (fan-out, partial failure aggregation)
  - Frontend component tests (Dashboard, Devices, Events, Settings, Layout)
  - Integration tests (poll→SQLite, poll→Prometheus, event→alert lifecycle)
- [x] Security audit — SSRF protection in alert providers, API key validation, rate limiting
  headers, input validation on all routes, CORS policy review, HTTPS-only scheme enforcement
  in all alert provider URL validation (reject `http://` URLs)
- [x] Defensive coding review — runtime config validation, shared state thread safety,
  atomic exporter writes, alert provider URL validation, SQLite lock timeout handling
- [x] Best practices review — type hint modernization (Python 3.10+ style), magic string
  extraction, import organisation, duplicate logic elimination
- [x] Modernization review — StrEnum usage, context managers for SQLite, deprecated API removal
- [x] Error handling completeness — classify all exception sites; ensure no silent swallows;
  document error catalog and error handling conventions
- [x] Test coverage gaps — fix any `ResourceWarning` (unclosed DB connections), achieve ≥90%
  Python coverage, ≥70% frontend coverage
- [x] Documentation accuracy — verify README matches actual commands, env vars, and API schemas;
  update test counts and coverage stats

> 🏁 **v1.0 release gate** — all Phase 4 items must be complete before tagging v1.0.

---

## Testing Backlog

- [x] NUTPoller integration test — mock NUT socket; verify full parse → `PowerSnapshot` round-trip
- [x] SNMPPoller integration test — mock pysnmp; verify OID mapping → `PowerSnapshot`
- [x] SQLite exporter integration test — verify schema, write, prune by days, prune by row count
- [x] CSV exporter integration test — verify file creation, row format, size-based rotation, and age pruning
- [x] Energy accumulator test — verify Wh integration across poll cycles, cumulative counter, cost calc
- [x] SNMPv3 integration test — verify authPriv mode connects and maps OIDs correctly
- [x] Scheduler persistence test — simulate restart and verify poll interval is restored from
  `runtime_config.json`
- [x] Alert lifecycle test — record N failures, verify alert fired; record success, verify reset

---

## Post-Release Enhancements

_Features planned for after v1.0. Not required for stable release._

---

## v1.1 — Power Quality & SLA Monitoring

### Power Quality SLA

- [ ] `SLAMonitor` — configurable thresholds for voltage deviation (`SLA_VOLTAGE_DEVIATION_PCT`),
  battery minimum (`SLA_BATTERY_MIN_PCT`), runtime minimum (`SLA_RUNTIME_MIN_SECONDS`), and
  load maximum (`SLA_LOAD_MAX_PCT`); per-dimension pass/fail flags
- [ ] `GET /api/diagnostics` SLA section — per-device SLA status embedded in diagnostics response
- [ ] `argus_sla_ok` Prometheus gauge — 1 = pass, 0 = fail, -1 = disabled (per device and dimension)

### Power Quality Score

- [ ] `PowerQualityScorer` — composite 0–100 score: voltage stability (30%), battery health (25%),
  load headroom (20%), runtime headroom (15%), temperature margin (10%); stored in
  `PowerSnapshot.quality_score`; exported via all exporters and `argus_quality_score` gauge

### Battery Health Trending

- [ ] Battery health history — track `battery_percent` and `runtime_seconds` at each poll;
  compute a rolling runtime-per-percent-capacity ratio over 30/90 days to detect gradual
  battery degradation; store trend in SQLite; expose via `GET /api/devices/{id}/battery-health`
- [ ] Battery health Prometheus gauge — `argus_battery_health_ratio` (current runtime÷rated
  runtime); drops below 1.0 as battery ages; pairs with Grafana alerting rules

### Maintenance Windows

- [ ] Maintenance window support — `POST /api/maintenance` to schedule a named window
  (start, end, affected device IDs); suppress all alerts for covered devices during the
  window; persist in `data/runtime_config.json`; expose active window in `/api/health`

### Code Quality & Testing

- [ ] Main loop tests — cover `build_dispatcher`, `build_alert_manager`, `_build_health_status`,
  pause toggle, environment validation, and `main()` startup restore
- [ ] Performance monitoring — Prometheus label cardinality management, SQLite WAL checkpoint,
  HTTP connection pooling for alert providers, async alert dispatch thread pool statistics
- [ ] Type alias extraction — `JsonDict`, `DeviceConfig`, `AlertConfig` aliases in `src/types.py`
  adopted across API routes and runtime_config

---

## v1.2 — Multi-Device & Integration

### Multi-Device Management

- [ ] Concurrent device polling — poll all configured devices in parallel using
  `ThreadPoolExecutor`; aggregate results; per-device failure tracking
- [ ] Per-device alert thresholds — configure `ALERT_FAILURE_THRESHOLD` per device, not globally
- [ ] Device tagging — add user-defined tags to devices (e.g., "rack-A", "primary-ups") for
  grouping in the UI and Grafana
- [ ] PDU per-outlet power monitoring — for SNMP PDUs that expose per-outlet OIDs (e.g.,
  APC AP8941 MIB, Raritan PX MIB), poll individual outlet load watts and on/off state;
  store as structured JSON in `PowerSnapshot.outlet_data`; expose per-outlet gauges in
  Prometheus as `argus_outlet_load_watts{device_id, outlet}`

### External Integrations

- [ ] Grafana Alloy agent config — starter config for scraping Argus metrics and shipping logs
  to Loki; included in docs
- [ ] Data export API — `GET /api/export/snapshots` (CSV or JSON) and
  `GET /api/export/events` for backup and migration
- [ ] Event annotations — `POST /api/events/{id}/annotate` — attach user notes to power events
  (e.g., "planned maintenance", "ISP storm", "router reboot")

---

## v1.3+ — Advanced Features

### Diagnostics & Analysis

- [ ] Anomaly detection — flag power snapshots that deviate significantly from rolling baseline
  (e.g., sudden voltage spike, battery drain faster than expected)
- [ ] Outage duration tracking — record outage start/end timestamps; `GET /api/outages` endpoint;
  `argus_outage_duration_seconds` Prometheus histogram
- [ ] Trend analysis — rolling averages, week-over-week power consumption comparison,
  load growth projection
- [ ] Time-of-day patterns — average load/power by hour of day and day of week to identify
  peak usage windows

### Device Control

- [ ] PDU outlet control — `POST /api/devices/{id}/outlets/{n}/toggle` backed by SNMP SET;
  confirmation required; audit-logged
- [ ] Graceful shutdown integration — trigger OS shutdown (via NUT `FSD` command or script hook)
  when battery reaches configurable critical floor; configurable delay and confirmation

### Alerting Enhancements

- [ ] Email alerting — SMTP provider; HTML and plain-text templates for power events
- [ ] Alert history — `GET /api/alert-history` endpoint; store sent alerts in SQLite with
  event type, provider, timestamp, and status
- [ ] Customisable alert message templates — Jinja2-based templates for each alert type;
  expose device name, metric values, and event context in the rendered message body;
  configurable per provider

### UI/UX Enhancements

- [ ] Dashboard customization — choose which metric cards to display; rearrange gauge layout
- [ ] Result filtering in history — filter snapshots by device, metric range, and date range
- [ ] Export charts — download power charts as PNG/SVG for reports
- [ ] Map / rack view — visual rack layout with per-device status colour overlay
