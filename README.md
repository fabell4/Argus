# Argus

Argus is a local-first power monitoring and control dashboard for UPS, PDU, sensor, and host telemetry. It is designed around NUT, SNMP-based devices, and optional host agents, while remaining fully functional without any external observability stack.

## Core Design Principles

### Local-first system of record

- SQLite is the primary source of truth
- All telemetry, device state, and events are stored locally
- Argus must continue working without Prometheus, Grafana, Alloy, or InfluxDB

### Optional observability integration

- Prometheus metrics export
- InfluxDB time-series export
- Grafana Alloy remote-write compatibility
- Grafana dashboards as an external visualization layer

### Multi-source telemetry model

- NUT polling for UPS devices
- SNMP polling for PDUs, UPS devices, and sensors
- Optional host agents or HTTP endpoints for system telemetry

## Architecture

```text
[ Devices ]
   │
   ├── UPS (NUT)
   ├── Smart PDU (SNMP)
   ├── Hosts (Agent / HTTP)
   │
   ▼
[ Argus Ingestion Layer ]
   │
   ├── Normalization Engine
   ├── Event Processor
   ├── Scheduling System
   │
   ▼
[ SQLite Storage ]
   │
   ├── Power Snapshots
   ├── Events
   ├── Device Registry
   │
   ▼
[ Argus UI + API Layer ]
   │
   ├── Dashboard
   ├── Historical Views
   ├── Event Timeline
   ├── Manual Controls
   │
   ▼
[ Optional Export Layer ]
   ├── Prometheus Metrics Endpoint
   ├── InfluxDB Exporter
   ├── Alloy Remote Write
```

## Core Components

### Ingestion layer

Responsible for device polling, retries, and error handling across NUT, SNMP, and optional HTTP host agents.

### Normalization engine

Maps heterogeneous source data into a canonical schema, including:

- `power_watts`
- `load_percent`
- `voltage`
- `battery_percent`
- `runtime_seconds`

### Event processor

Detects state transitions between snapshots and emits structured events such as:

- `on_battery`
- `power_restored`
- `battery_low`
- `shutdown_initiated`
- `threshold_crossed`

### Storage layer

SQLite is the authoritative database. Initial tables are expected to include:

#### `devices`

- `id`
- `name`
- `type`
- `connection_config`

#### `power_snapshots`

- `timestamp`
- `device_id`
- `watts`
- `load_percent`
- `voltage`
- `battery_percent`
- `runtime_seconds`

#### `events`

- `timestamp`
- `device_id`
- `event_type`
- `metadata`

### Scheduling system

- Configurable polling intervals per device
- Manual trigger support
- Failure backoff behavior

### UI layer

The dashboard should provide:

- Real-time system status
- Power timeline graphs
- UPS state visualization
- Event history timeline
- Device health overview
- Manual polling controls

## Optional integrations

### Prometheus

- Expose a `/metrics` endpoint
- Export normalized snapshot metrics for external scraping

### InfluxDB

- Support optional time-series export
- Enable long-term retention and analytics outside the local node

### Grafana Alloy

- Provide compatibility with remote write or pipeline-based ingestion

## Data flow

### Primary flow

1. Poll device data from NUT, SNMP, or a host agent
2. Normalize the result into the canonical telemetry schema
3. Store the snapshot in SQLite
4. Evaluate transitions and persist structured events
5. Update the dashboard and API state

### Optional export flow

6. Export metrics to Prometheus, InfluxDB, or Alloy when configured

## Relationship to Hermes

Argus follows the same high-level pattern as Hermes:

| Hermes | Argus |
| --- | --- |
| Run test | Poll device |
| Store result | Store snapshot |
| Schedule tests | Schedule polling |
| Manual test | Manual refresh |
| SQLite DB | SQLite DB |
| Optional InfluxDB | Optional InfluxDB |
| Grafana export | Grafana export |

## MVP scope

### Phase 1

- SQLite storage
- NUT integration
- Basic SNMP polling
- Simple dashboard UI

### Phase 2

- Event system
- Device registry
- Scheduling system
- Historical graphs

### Phase 3

- Prometheus export
- InfluxDB integration
- Alloy compatibility

## Future enhancements

- Multi-node Argus clustering
- Distributed device polling
- Advanced alerting engine
- Power usage forecasting
- UPS failure prediction

## Summary

Argus is intended to be a self-contained power observability platform that treats SQLite as the single source of truth and external observability tooling as optional add-ons.
