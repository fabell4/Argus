# Changelog

<!-- markdownlint-disable MD024 -- Duplicate headings are expected in changelogs for version sections -->

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

---

## [0.3.11-beta] - 2026-06-01

### Fixed

- **GitHub Pages custom domain** — added `docs/CNAME` with `argus-docs.greenflametech.com`
  and updated `docs/_config.yml` to set `url: https://argus-docs.greenflametech.com` and
  `baseurl: ""` so Jekyll asset paths resolve correctly under the custom domain.

---

## [0.3.10-beta] - 2026-06-01

### Fixed

- **`create_github_release.py` lint errors** — renamed module-level variables to `UPPER_CASE`
  constants, added explicit `encoding="utf-8"` to all `open()` calls, narrowed broad
  `Exception` catch to `OSError`, and added explicit `check=False` to the initial
  `subprocess.run` call to satisfy `W1510:subprocess-run-check`.

---

## [0.3.9-beta] - 2026-06-01

### Added

- **GitHub Pages Jekyll deployment workflow** — added `.github/workflows/docs.yml` to build
  and publish the `docs/` site via `actions/jekyll-build-pages` so the hacker theme and
  layout are applied correctly on GitHub Pages.
- **Jekyll plugins config fix** — added `jekyll-relative-links` to the `plugins` list in
  `docs/_config.yml` to match the Gemfile and enable relative link resolution.

---

## [0.3.8-beta] - 2026-06-01

### Fixed

- **GitHub Actions workflow validation failure** — replaced invalid `secrets.*`
  references in `if:` expressions with job-level `env.GHCR_PAT` checks in
  `link-ghcr-package.yml` to satisfy workflow expression context rules.

---

## [0.3.7-beta] - 2026-06-01

### Fixed

- **Release republish via non-public remotes** — incremented release to `v0.3.7-beta`
  to retrigger downstream release/publish automation without direct pushes to the
  public GitHub `Argus` repository.

---

## [0.3.6-beta] - 2026-06-01

### Fixed

- **GHCR publish token fallback for package ACL mismatches** — updated
  `link-ghcr-package.yml` to use `GHCR_PAT` (if configured) as a fallback to
  `GITHUB_TOKEN`, standardised GHCR login to `github.repository_owner`, and
  improved preflight diagnostics for GHCR `404` metadata responses that can
  mask package-level permission issues.

---

## [0.3.5-beta] - 2026-06-01

### Fixed

- **GHCR publish 403 on blob HEAD during buildx export** — disabled provenance/SBOM
  attestation upload in the GitHub GHCR publish workflow (`provenance: false`, `sbom: false`)
  to force a plain multi-arch image manifest push path

---

## [0.3.4-beta] - 2026-06-01

### Fixed

- **GHCR publish workflow failure and Node 20 deprecation warning** — upgraded
  `actions/checkout` to `v6.0.2` in GitHub workflows and added a GHCR preflight access check
  to fail early with actionable diagnostics when package permissions block `GITHUB_TOKEN`

---

## [0.3.3-beta] - 2026-06-01

### Fixed

- **GHCR package not linked to repository (architectural fix)** — moved GHCR build and push
  entirely to GitHub Actions (`link-ghcr-package.yml`), which now triggers automatically on
  `push: tags: v*`; Forgejo only pushes to the private registry; using `GITHUB_TOKEN` on the
  GitHub Actions runner is the only mechanism that causes GitHub to natively link the package

---

## [0.3.2-beta] - 2026-06-01

### Fixed

- **GHCR package still not linked after v0.3.1-beta** — reverted Forgejo build-and-push job
  from `docker/build-push-action` (incompatible with container-based Forgejo runners) back to
  plain `docker build` / `docker push`; replaced `imagetools create --annotation` approach in
  `link-ghcr-package.yml` with a simple `docker pull` + `docker push` via `GITHUB_TOKEN`,
  which is the only mechanism GitHub recognises for auto-linking a GHCR package to a repository

---

## [0.3.1-beta] - 2026-06-01

### Fixed

- **Branch protection not restored after release** — Forgejo release pipeline now saves branch
  protection rules and rulesets before disabling them for the force-push, then restores them
  automatically after the Forgejo release is created
- **GHCR container package not linked to repository** — replaced `docker build` + manual push
  with `docker/build-push-action` which correctly sets `org.opencontainers.image.source` on
  the pushed manifest; GitHub now auto-links the package to the Argus repository

### Chore

- **Remove Claude from contributors** — added `.mailmap` mapping Claude commit author to
  the canonical maintainer identity; added `.markdownlintignore` to exclude `.mailmap` from
  markdown linting

---

## [0.3.0-beta] - 2026-06-01

### Added

- **Comprehensive test suite** — 372 Python tests covering all core modules: `NUTPoller`,
  `SNMPPoller`, `SQLiteExporter`, `CSVExporter`, `EnergyAccumulator`, `PrometheusExporter`,
  `InfluxDBExporter`, `LokiExporter`, `EventProcessor`, `AlertManager`, alert providers,
  all API routes, `RuntimeConfig`, and `SnapshotDispatcher`; 94% overall coverage (≥90%
  gate met); all tests pass in 2.04 s

### Fixed

- **GHCR package linking** — consolidated pipeline fixes from v0.2.3-beta through v0.2.5-beta:
  secure `extraheader` credential passing to GitHub, `pip install semgrep` on GitHub runners,
  and `docker buildx imagetools create --annotation` to rewrite the
  `org.opencontainers.image.source` OCI manifest annotation so the package links to
  `Argus` instead of `argus-dev`

---

## [0.2.5-beta] - 2026-06-01

### Fixed

- **GHCR package linking** — replaced the naive `docker pull`/`docker push` approach in
  `link-ghcr-package.yml` with `docker buildx imagetools create --annotation` which rewrites
  the `org.opencontainers.image.source` OCI annotation on the manifest index to point at
  the `Argus` repository before pushing via `GITHUB_TOKEN`. The old approach re-used the
  existing manifest unchanged, so GitHub kept the package linked to `argus-dev` (the repo
  that first pushed via `GITHUB_TOKEN`). The new approach forces GitHub to re-link by
  updating the annotation and performing a fresh authenticated push from `Argus`.

---

## [0.2.4-beta] - 2026-06-01

### Fixed

- **GitHub CI** — added `pip install semgrep` before the Semgrep SAST step; the tool is not
  pre-installed on `ubuntu-24.04` runners and was causing the Python checks job to fail with
  exit code 127.

---

## [0.2.3-beta] - 2026-06-01

### Fixed

- **CI workflow** — switched git remote authentication from PAT-in-URL to `http.extraheader`
  (matches Hermes pattern) to prevent token exposure in git logs; increased GHCR package-link
  dispatch sleep from 15 s to 30 s to reduce race with GitHub workflow indexing.

---

## [0.2.2-beta] - 2026-06-01

### Fixed

- **CI workflow** — added `sha-check: 'false'` to the `forgejo-release@v2` step so
  `workflow_dispatch` re-runs no longer fail the SHA guard (which only applies to
  `push: tags:` triggers).

---

## [0.2.1-beta] - 2026-06-01

### Fixed

- **CI workflow** — added `DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN` secrets and guarded
  GHCR login, push, and package-visibility steps with `if:` checks so the pipeline
  degrades gracefully when optional registry secrets are absent.

---

## [0.2.0-beta] - 2026-06-01

### Added

- **Testing backlog completed** — full integration test coverage for all core subsystems:
  `NUTPoller`, `SNMPPoller` (including SNMPv3 authPriv), `SQLiteExporter`, `CSVExporter`
  (rotation + age pruning), `EnergyAccumulator`, and alert lifecycle (threshold, fire,
  reset); scheduler persistence test verifies poll interval is restored from
  `runtime_config.json` on restart.
- **Grafana Alloy config** — `grafana/argus.alloy` starter config for scraping Argus
  Prometheus metrics and shipping structured logs to Loki.

### Fixed

- **FastAPI 0.115 compatibility** — `DELETE /api/devices/{id}` (HTTP 204) now declares
  `response_model=None` and `response_class=Response` to satisfy the stricter
  no-response-body assertion introduced in FastAPI 0.115.
- **Power exporter bug** — corrected calculation error in power export path.

### Changed

- **Grafana dashboard** — updated `argus-power-monitoring.json` with Loki log panel and
  refined variable inputs.

### Security

- **Test URL scheme** — replaced all `http://` fixture URLs in `test_misc_modules.py`
  with `https://` to resolve SonarQube Security Hotspot `python:S5332`.

---

## [0.1.0-beta] - 2026-05-29

### Added

- **Initial architecture** — Full project scaffold mirroring Hermes design pattern, adapted for
  local-first power monitoring (UPS, PDU, sensors) via NUT and SNMP.
- **Two-process architecture** — `argus-scheduler` (APScheduler + pollers) and `argus-api`
  (FastAPI) run as separate containers sharing `argus-data` and `argus-logs` volumes.
- **NUT poller** — Polls UPS devices via raw NUT socket protocol (`LIST VAR`). Maps NUT variables
  to canonical `PowerSnapshot` fields; derives `power_watts` from nominal power × load percent
  when a direct reading is unavailable.
- **NUT auto-discovery** — `NUT_AUTO_DISCOVER=true` (default) issues `LIST UPS` on startup and
  registers all reported UPS devices automatically; manual `NUT_UPS_NAME` list retained as fallback.
- **SNMP poller** — Optional pysnmp-based poller for PDUs and sensors using RFC 1628 UPS-MIB OIDs.
- **SNMPv3 support** — `snmp_poller` extended with authPriv authentication using
  `SNMP_AUTH_PROTOCOL`/`SNMP_PRIV_PROTOCOL` and corresponding key variables.
- **PowerSnapshot model** — Canonical telemetry unit with full validation: tz-aware timestamp,
  non-empty device ID, load/battery percent 0–100, power_watts ≥ 0.
- **UPS metadata** — `PowerSnapshot` extended with `ups_model`, `ups_serial`, `ups_firmware`,
  and `ups_mfr` fields populated from NUT variable introspection.
- **Device registry** — `DeviceRegistry` tracks all polled devices and their last-seen metadata;
  persists across restarts via `data/runtime_config.json`.
- **Multi-device polling** — Scheduler fans out to all registered NUT and SNMP devices in a
  single poll cycle.
- **Retry logic** — NUT and SNMP pollers retry transient connection failures with exponential
  backoff before marking a device offline.
- **Exporters** — SQLite (WAL, retention by days + row count), Prometheus (Gauges with
  device_id/device_type labels), InfluxDB (optional, `power_snapshot` measurement).
- **SQLite WAL mode, VACUUM, and indexes** — `sqlite_exporter` now opens the database in WAL
  mode, creates composite indexes for common query patterns, and runs `PRAGMA optimize` on
  startup.
- **Retention audit** — SQLite exporter enforces both `SQLITE_RETENTION_DAYS` and
  `SQLITE_MAX_ROWS` on every write cycle.
- **CSV exporter** — `CsvExporter` writes snapshots to rotating CSV files with configurable
  max file size and age pruning.
- **Energy accumulator** — `EnergyAccumulator` uses trapezoidal integration for cumulative kWh
  tracking; optional cost estimation via `ENERGY_RATE_PER_KWH`.
- **Loki exporter** — `LokiExporter` ships structured snapshot logs to a Grafana Loki instance.
- **Prometheus cardinality management** — `PROMETHEUS_DISABLE_LABELS` env var omits
  `device_id`/`device_type` labels to reduce time-series cardinality in large deployments.
- **Event processor** — Detects `on_battery`, `power_restored`, and `battery_low` transitions
  by comparing successive snapshots per device.
- **Additional power events** — `device_offline`, `device_online`, `shutdown_initiated`, and
  `threshold_crossed` events added to `EventProcessor`.
- **Alert manager** — Failure-threshold alerting with cooldown, dispatched via
  `ThreadPoolExecutor`. Providers: Webhook, Gotify, ntfy, Apprise.
- **Alert API** — `GET /api/alerts`, `PUT /api/alerts`, and `POST /api/alerts/test` endpoints
  backed by `AlertConfigSchema` Pydantic model; supports Webhook, Gotify, ntfy, and Apprise.
- **FastAPI** — REST API with API key auth, rate limiting, request-size limit middleware,
  security headers, and CORS configuration.
- **API routes** — `/api/snapshots`, `/api/events`, `/api/devices`, `/api/trigger`,
  `/api/config`, `/api/alerts`, `/api/diagnostics`, `/api/health`.
- **Poll pause/resume** — `/api/config` `PUT` accepts `polling_paused: true/false`; scheduler
  respects the flag without restarting.
- **Runtime config** — Persistent `data/runtime_config.json` with atomic writes; sentinel files
  for poll trigger and running state.
- **Environment validation** — `src/config.py` validates all required/typed env vars at import
  time and raises descriptive errors on misconfiguration.
- **React 18 TypeScript frontend** — Dashboard (PowerGauge, PowerChart, EventsTable),
  Settings page, ArgusContext provider, typed API client.
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
- **Grafana dashboard** — Pre-built dashboard JSON at `grafana/argus-power-monitoring.json`
  covering power/load/battery gauges, event timeline, and energy totals.
- **Docker** — Multi-stage Dockerfile (Node 20 frontend build + Python 3.12-slim runtime),
  non-root `argus` user, exposes 8000/9090/9100.
- **Docker HEALTHCHECK** — API container health check wired to `/api/health`; scheduler
  container checks the health server on port 9100.
- **Multi-arch Docker build** — CI produces `linux/amd64` and `linux/arm64` images via
  `docker buildx`.
- **CI pipeline** — Forgejo Actions: full lint/type-check/security/tests pipeline. Coverage
  gate ≥85%.
- **SonarQube** — `sonar-project.properties` wired for Python + TypeScript analysis with
  coverage and external issue reports.
- **Dependabot** — Weekly updates for pip, npm, and GitHub Actions dependencies.
