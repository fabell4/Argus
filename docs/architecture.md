---
layout: default
title: "Architecture"
---

# 🏗️ Architecture Overview

Argus is designed as a two-container system that continuously monitors power infrastructure via NUT
and SNMP, exports telemetry to multiple observability destinations, and serves a React frontend
through a FastAPI backend.

---

## 🏗️ System Architecture

### Data Flow

```mermaid
flowchart TD
    subgraph API_CONTAINER["argus-api container"]
        API["**FastAPI REST API**\nsrc/api/main.py\n:8000"]
        REACT["**React Frontend**\nfrontend/dist\n(served by FastAPI)"]
    end

    subgraph SCHED_CONTAINER["argus-scheduler container"]
        MAIN["**main.py**\nEntry point + APScheduler"]
        NUT["**NUTPoller**\nsrc/services/nut_poller.py"]
        SNMP["**SNMPPoller**\nsrc/services/snmp_poller.py"]
        MODEL["**PowerSnapshot**\nsrc/models/power_snapshot.py"]
        DISP["**SnapshotDispatcher**\nsrc/snapshot_dispatcher.py"]
        EVT["**EventProcessor**\nsrc/services/event_processor.py"]
        ALERT["**AlertManager**\nsrc/services/alert_manager.py"]
        HEALTH["**HealthServer**\n:9100/health"]
        SQLITE["SQLiteExporter"]
        PROM["PrometheusExporter\n:9090/metrics"]
        INFLUX["InfluxDBExporter"]
        LOKI["LokiExporter"]
        CSV["CSVExporter"]
        ENERGY["EnergyAccumulator"]
    end

    DEVICES[("**Power Devices**\nUPS (NUT)\nPDU / Sensors (SNMP)")]
    DATA_VOL[("**Shared Volume**\nargus.db\nruntime_config.json")]
    ALERT_DEST[("**Alert Destinations**\nWebhook, Gotify,\nntfy, Apprise")]

    REACT -- "HTTP GET/POST" --> API
    API -- "POST /api/trigger\nPUT /api/config\nPUT /api/alerts\nPOST /api/devices" --> DATA_VOL
    API -- "GET /api/snapshots\nGET /api/events\nGET /api/energy" --> DATA_VOL
    MAIN -- "polls on schedule" --> NUT
    MAIN -- "polls on schedule" --> SNMP
    NUT -- "PowerSnapshot" --> MODEL
    SNMP -- "PowerSnapshot" --> MODEL
    DEVICES -- "NUT protocol / SNMP" --> NUT
    DEVICES -- "SNMP" --> SNMP
    MODEL --> DISP
    MODEL --> EVT
    EVT -- "event detected" --> ALERT
    DISP --> SQLITE
    DISP --> PROM
    DISP --> INFLUX
    DISP --> LOKI
    DISP --> CSV
    DISP --> ENERGY
    SQLITE -- "writes" --> DATA_VOL
    ENERGY -- "writes" --> DATA_VOL
    ALERT -- "on threshold" --> ALERT_DEST

    style API fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style REACT fill:#1565c0,stroke:#90caf9,color:#ffffff
    style MAIN fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style NUT fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style SNMP fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style MODEL fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style DISP fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style EVT fill:#6a1b9a,stroke:#ce93d8,color:#ffffff
    style ALERT fill:#c62828,stroke:#ef5350,color:#ffffff
    style HEALTH fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style SQLITE fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style PROM fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style INFLUX fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style LOKI fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style CSV fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style ENERGY fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style DATA_VOL fill:#f57c00,stroke:#ffb74d,color:#ffffff
    style ALERT_DEST fill:#c62828,stroke:#ef5350,color:#ffffff
    style DEVICES fill:#0277bd,stroke:#81d4fa,color:#ffffff
```

### 🌐 Deployment Topology

```mermaid
flowchart LR
    subgraph ARGUS_HOST["Argus Host"]
        subgraph SCHED["argus-scheduler"]
            PROM_EP["PrometheusExporter\n:9090/metrics"]
            HEALTH_EP["HealthServer\n:9100/health"]
            LOKI_EXP["LokiExporter"]
            ALERT_MGR["AlertManager"]
        end
        subgraph API_C["argus-api"]
            API["FastAPI + React UI\n:8000"]
        end
        SHARED_VOL[("argus-data volume\nargus.db\nruntime_config.json")]
    end

    subgraph POWER_INFRA["Power Infrastructure"]
        NUT_DAEMON["NUT Daemon\n:3493"]
        SNMP_DEV["PDU / Sensors\n(SNMP)"]
    end

    subgraph OBS_HOST["Observability Host"]
        PROMETHEUS["Prometheus\n:9090"]
        LOKI["Loki\n:3100"]
        INFLUX["InfluxDB\n:8086"]
        GRAFANA["Grafana\n:3000"]
    end

    subgraph ALERT_SVCS["Alert Services (optional)"]
        GOTIFY["Gotify"]
        NTFY["ntfy"]
        APPRISE["Apprise API"]
        WEBHOOK["Custom Webhook"]
    end

    SCHED -- "polls every N min" --> NUT_DAEMON
    SCHED -- "SNMP polls" --> SNMP_DEV
    SCHED -- "reads/writes" --> SHARED_VOL
    API -- "reads" --> SHARED_VOL
    PROMETHEUS -- "scrapes :9090/metrics" --> PROM_EP
    LOKI_EXP -- "pushes logs" --> LOKI
    ALERT_MGR -- "HTTPS POST" --> GOTIFY
    ALERT_MGR -- "HTTPS POST" --> NTFY
    ALERT_MGR -- "HTTPS POST" --> APPRISE
    ALERT_MGR -- "HTTPS POST" --> WEBHOOK
    GRAFANA -- "queries" --> PROMETHEUS
    GRAFANA -- "queries" --> LOKI
    GRAFANA -- "queries" --> INFLUX
```

---

## 🔧 Component Reference

### argus-scheduler

The long-running background process responsible for all data collection.

| Component | Path | Responsibility |
| --- | --- | --- |
| `main.py` | `src/main.py` | Entry point, APScheduler setup, signal handling |
| `NUTPoller` | `src/services/nut_poller.py` | Queries NUT daemon via `PyNUTClient` |
| `SNMPPoller` | `src/services/snmp_poller.py` | Queries SNMP devices via PySNMP |
| `SnapshotDispatcher` | `src/snapshot_dispatcher.py` | Fans out `PowerSnapshot` to all enabled exporters |
| `EventProcessor` | `src/services/event_processor.py` | Detects state transitions; emits `PowerEvent` records |
| `AlertManager` | `src/services/alert_manager.py` | Fires notifications when event conditions are met |
| `DeviceRegistry` | `src/services/device_registry.py` | Persistent device catalogue (JSON-backed) |
| `HealthServer` | `src/services/health_server.py` | Lightweight HTTP health endpoint on `HEALTH_PORT` |

### argus-api

The HTTP server that serves both the REST API and the React SPA.

| Component | Path | Responsibility |
| --- | --- | --- |
| `main.py` | `src/api/main.py` | FastAPI app factory, middleware, static file serving |
| `auth.py` | `src/api/auth.py` | API key validation, rate limiting |
| `routes/snapshots` | `src/api/routes/snapshots.py` | Paginated power snapshot history |
| `routes/events` | `src/api/routes/events.py` | Paginated power event history |
| `routes/devices` | `src/api/routes/devices.py` | Device registry CRUD |
| `routes/alerts` | `src/api/routes/alerts.py` | Alert provider configuration |
| `routes/config` | `src/api/routes/config.py` | Runtime scheduler configuration |
| `routes/energy` | `src/api/routes/energy.py` | Cumulative kWh totals |
| `routes/trigger` | `src/api/routes/trigger.py` | Manual poll trigger |
| `routes/diagnostics` | `src/api/routes/diagnostics.py` | Last-poll diagnostics |

---

## 📤 Exporters

| Exporter | Key | Description |
| --- | --- | --- |
| `SQLiteExporter` | `sqlite` | Writes snapshots to `argus.db`; enforces retention |
| `PrometheusExporter` | `prometheus` | Exposes Gauge metrics at `/metrics` |
| `InfluxDBExporter` | `influxdb` | Writes points to InfluxDB v2 |
| `LokiExporter` | `loki` | Pushes structured log lines to Loki |
| `CSVExporter` | `csv` | Appends rows to a rotating CSV file |
| `EnergyAccumulatorExporter` | `energy` | Accumulates kWh from watt-second snapshots |

Enable exporters via `ENABLED_EXPORTERS=sqlite,prometheus,influxdb` (comma-separated).

---

## ⚙️ Runtime Configuration

Both containers share the `argus-data` volume. The scheduler watches
`data/runtime_config.json` for changes written by the API, enabling zero-restart
reconfiguration of:

- Poll interval
- Enabled exporters
- NUT connection settings
- Alert provider configuration
- Scheduler pause / resume

---

## 📊 Grafana Dashboard

**Import pre-built dashboard:**

1. Download `docs/grafana-dashboard.json`
2. In Grafana: **+ → Import → Upload JSON file**
3. Select Prometheus as the datasource
4. Dashboard includes:

   - Per-device power draw and load percentage charts
   - Battery charge and runtime remaining panels
   - UPS status and event timeline
   - Input/output voltage and temperature gauges

---

## 🌐 Ports Summary

| Container | Port | Protocol | Purpose |
| --- | --- | --- | --- |
| `argus-api` | `8000` | HTTP | REST API + React UI |
| `argus-scheduler` | `9090` | HTTP | Prometheus `/metrics` (when enabled) |
| `argus-scheduler` | `9100` | HTTP | Health check `/health` |
