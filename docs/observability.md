---
layout: default
title: "Observability"
---

# 📊 Observability — Metrics & Logs

Argus supports two patterns for shipping metrics and logs to Grafana, Grafana Cloud, or a
self-hosted Grafana stack.  Both are optional and can be mixed: for example, you might send
metrics through Alloy but push logs directly to Loki.

---

## Choosing a mode

| | **Direct mode** | **Alloy relay mode** |
| --- | --- | --- |
| Argus pushes logs to | Loki directly | Alloy (Alloy forwards to Loki) |
| Metrics scraped by | Prometheus / Mimir directly | Alloy (Alloy remote-writes) |
| Extra component required | No | Alloy ≥ v1.0 |
| Good for | Existing Prometheus + Loki setups | Grafana Cloud or Alloy-first stacks |
| `grafana/argus.alloy` needed | No | Yes |

---

## Mode A — Direct (no Alloy)

Argus exports metrics and logs directly to Prometheus and Loki.  No additional file is needed.

### 1. Enable exporters

In your `.env` or `docker-compose.yml` environment block:

```env
# Enable the Prometheus scrape endpoint and the Loki push exporter
ENABLED_EXPORTERS=sqlite,prometheus
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090          # default — Argus /metrics is on this port

# Point directly at your Loki instance
LOKI_URL=http://loki:3100
LOKI_JOB_LABEL=argus_power    # appears as the `job` stream label in Loki
LOKI_TIMEOUT_SECONDS=5
```

### 2. Configure a Prometheus scrape job

Add a job to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: argus
    scrape_interval: 1m
    static_configs:
      - targets:
          - argus-scheduler:9090   # adjust host if Prometheus is outside Compose
```

### 3. Exposed metrics

| Metric | Labels | Description |
| -------- | -------- | ------------- |
| `argus_power_watts` | `device_id`, `device_type` | Instantaneous power draw (W) |
| `argus_load_percent` | `device_id`, `device_type` | Device load (%) |
| `argus_voltage_volts` | `device_id`, `device_type` | Input/output voltage (V) |
| `argus_battery_percent` | `device_id`, `device_type` | UPS battery charge (%) |
| `argus_runtime_seconds` | `device_id`, `device_type` | UPS estimated runtime (s) |
| `argus_temperature_celsius` | `device_id`, `device_type` | Device temperature (°C) |

> **Label-free mode** — If you have many devices and want to avoid high cardinality, set
> `PROMETHEUS_DISABLE_LABELS=true`.  All gauges will be published without `device_id` /
> `device_type` labels.

---

## Mode B — Alloy relay

Use this mode when you already run Grafana Alloy or prefer an Alloy-first pipeline (e.g.
Grafana Cloud with the Alloy collector).  Alloy scrapes Argus and remote-writes metrics; it
also opens a Loki-compatible HTTP endpoint so Argus can push logs through Alloy instead of
directly to Loki.

### Architecture

``` text
Argus scheduler
  ├─ /metrics (Prometheus scrape endpoint)  ──────► Alloy ──► Prometheus / Mimir / Grafana Cloud
  └─ LokiExporter → HTTP push to Alloy :12345  ──► Alloy ──► Loki / Grafana Cloud Logs
```

### 1. Copy `argus.alloy` into your Alloy config directory

The file lives at `grafana/argus.alloy` in this repository.

```bash
cp grafana/argus.alloy /etc/alloy/argus.alloy
```

### 2. Load it from your primary Alloy config

#### Option A — glob path (recommended)

Pass multiple paths to the Alloy binary so it loads every `.alloy` file in the directory:

```bash
# systemd unit or container command
alloy run /etc/alloy/*.alloy
```

#### Option B — explicit import

In your existing `config.alloy`:

```alloy
import.file "argus" {
  filename = "/etc/alloy/argus.alloy"
}
```

> **Component name collisions** — `argus.alloy` uses the component labels `"argus"` and
> `"grafana"`.  If your existing config already has `prometheus.remote_write "grafana"` or
> `loki.write "grafana"`, either rename the components in `argus.alloy` or use the import
> approach (imports are namespaced and cannot collide).

### 3. Set environment variables

Alloy reads these at startup.  Set them in the Alloy service environment, a `.env` file, or
Docker Compose:

| Variable | Required | Default | Description |
| -------- | -------- | ------- | ----------- |
| `ARGUS_METRICS_ADDRESS` | No | `argus-scheduler:9090` | `host:port` of Argus metrics endpoint |
| `REMOTE_WRITE_URL` | **Yes** | — | Prometheus remote write URL |
| `REMOTE_WRITE_USERNAME` | No | — | Basic-auth username (Grafana Cloud: instance ID) |
| `REMOTE_WRITE_PASSWORD` | No | — | Basic-auth password / API key |
| `LOKI_PUSH_URL` | **Yes** | — | Loki push URL |
| `LOKI_USERNAME` | No | — | Loki basic-auth username |
| `LOKI_PASSWORD` | No | — | Loki basic-auth password / API key |
| `ALLOY_CLUSTER_LABEL` | No | `argus` | Value of the `cluster` external label |

**Grafana Cloud example:**

```env
REMOTE_WRITE_URL=https://prometheus-prod-01-eu-west-0.grafana.net/api/prom/push
REMOTE_WRITE_USERNAME=123456
REMOTE_WRITE_PASSWORD=glc_xxxxxxxxxxxxxxxxxxxx

LOKI_PUSH_URL=https://logs-prod-eu-west-0.grafana.net/loki/api/v1/push
LOKI_USERNAME=123456
LOKI_PASSWORD=glc_xxxxxxxxxxxxxxxxxxxx

ALLOY_CLUSTER_LABEL=home-lab
```

**Self-hosted Mimir + Loki example:**

```env
REMOTE_WRITE_URL=http://mimir:9009/api/v1/push
LOKI_PUSH_URL=http://loki:3100/loki/api/v1/push
ALLOY_CLUSTER_LABEL=argus
```

### 4. Configure Argus to point at Alloy

In your Argus `.env`:

```env
ENABLED_EXPORTERS=sqlite,prometheus
PROMETHEUS_ENABLED=true

# Point LokiExporter at Alloy's receiver port, NOT at real Loki
LOKI_URL=http://alloy:12345
```

If Alloy runs in a separate container, expose port 12345:

```yaml
# docker-compose.override.yml
services:
  alloy:
    ports:
      - "12345:12345"
```

### 5. Reload Alloy

```bash
# systemd
sudo systemctl reload alloy

# Docker
docker compose restart alloy
```

---

## Logs-only or metrics-only Alloy

`argus.alloy` can be trimmed to only what you need.

**Metrics only (no log relay)** — delete the `loki.source.api` and `loki.write` blocks and
point `LOKI_URL` directly at Loki.

**Logs only (no Alloy scraping)** — delete the `prometheus.scrape` and
`prometheus.remote_write` blocks and add a standard Prometheus scrape job as shown in Mode A.

---

## Verifying the pipeline

### Check Alloy component health

```bash
# Alloy UI (default port 12345 conflicts — Alloy's own UI is on 12345 by default.
# If using the log receiver, set --server.http.listen-addr to a different port,
# e.g. --server.http.listen-addr=0.0.0.0:12346)
open http://alloy-host:12346
```

Navigate to **Graph** to see whether `prometheus.scrape.argus` and `loki.source.api.argus_receiver`
are healthy (green).

### Verify metrics are arriving

In Grafana Explore, run:

```promql
{job="argus"}
argus_power_watts
```

### Verify logs are arriving

In Grafana Explore (Loki datasource):

```logql
{job="argus_power"}
```

---

## Grafana dashboard

A pre-built dashboard is included at `grafana/argus-power-monitoring.json`.  Import it via
**Dashboards → Import** and select your Prometheus and Loki datasources.

---

## Port reference

| Port | Service | Protocol | Notes |
| ---- | ------- | -------- | ----- |
| 9090 | Argus scheduler | HTTP | Prometheus `/metrics` scrape endpoint |
| 9100 | Argus scheduler | HTTP | Health endpoint (`/health`) |
| 8000 | Argus API | HTTP | REST API + React frontend |
| 12345 | Alloy log receiver | HTTP | Loki-compatible push endpoint (Alloy relay mode only) |
