---
layout: default
title: "API Reference"
---

# 🔌 API Reference

Complete REST API documentation for the Argus FastAPI backend.

---

## 🔗 Base URL

```text
http://localhost:8000/api
```

Replace `localhost:8000` with your server address.

---

## 🔑 Authentication

### API Key Authentication

When `API_KEY` is set, **protected endpoints** require an `X-Api-Key` header:

```bash
curl -X POST http://localhost:8000/api/trigger \
  -H "X-Api-Key: your-api-key-here"
```

**Public endpoints** (most GET requests) do not require authentication.

### Generate a Secure API Key

```bash
# Option 1: Python secrets module (recommended)
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# Option 2: OpenSSL
openssl rand -hex 32
```

**Requirements:**

- Minimum 32 characters enforced at startup
- Application exits with an error message if `API_KEY` is set but too short

### Disabling Authentication

Leave `API_KEY` unset in `.env`. **Not recommended for production.**

---

## 🚦 Rate Limiting

Protected endpoints are rate-limited per API key:

- **Default:** 60 requests per 60-second sliding window
- **Configurable:** `RATE_LIMIT_PER_MINUTE` in `.env`
- **Response on limit:** `429 Too Many Requests` with `Retry-After` header

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
Content-Type: application/json

{ "detail": "Rate limit exceeded. Try again in 60 seconds." }
```

---

## 🌐 Public Endpoints

### 🩺 Health Check

```http
GET /api/health
```

**Response:**

```json
{
  "status": "healthy",
  "scheduler_running": true,
  "uptime_seconds": 3600
}
```

---

### 📊 Snapshots

#### List Snapshots

```http
GET /api/snapshots
```

**Query parameters:**

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `page` | integer | `1` | Page number (≥ 1) |
| `page_size` | integer | `50` | Items per page (1–200) |
| `device_id` | string | _(none)_ | Filter by device ID |

**Response:**

```json
{
  "page": 1,
  "page_size": 50,
  "total": 1234,
  "items": [
    {
      "id": 1,
      "timestamp": "2026-05-27T10:00:00Z",
      "device_id": "ups-main",
      "device_type": "ups",
      "power_watts": 450.0,
      "load_percent": 55.0,
      "voltage": 120.0,
      "battery_percent": 100.0,
      "runtime_seconds": 3600.0,
      "ups_status": "OL",
      "temperature_c": null
    }
  ]
}
```

#### Latest Snapshot

```http
GET /api/snapshots/latest
```

Returns the most recent snapshot (all devices) or filtered by `?device_id=`.

---

### 🔔 Events

#### List Events

```http
GET /api/events
```

**Query parameters:**

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `page` | integer | `1` | Page number |
| `page_size` | integer | `50` | Items per page (1–200) |
| `device_id` | string | _(none)_ | Filter by device |
| `event_type` | string | _(none)_ | Filter by type (e.g. `on_battery`) |

**Response:**

```json
{
  "page": 1,
  "page_size": 50,
  "total": 42,
  "items": [
    {
      "id": 1,
      "timestamp": "2026-05-27T09:00:00Z",
      "device_id": "ups-main",
      "event_type": "on_battery",
      "metadata": { "previous_status": "OL", "battery_percent": 100.0 }
    }
  ]
}
```

**Event types:**

| Value | Trigger |
| --- | --- |
| `on_battery` | UPS switched from AC to battery |
| `power_restored` | AC power returned |
| `battery_low` | Battery charge below low threshold |
| `shutdown_initiated` | Battery hit floor percentage (`SHUTDOWN_BATTERY_FLOOR_PCT`) |
| `threshold_crossed` | Load % or temperature exceeded configured limit |
| `device_offline` | Device missed `DEVICE_OFFLINE_MISSED_POLLS` consecutive polls |
| `device_online` | Device reachable again after offline period |

---

### 🖥️ Devices

#### List Devices

```http
GET /api/devices
```

**Response:**

```json
[
  {
    "id": "ups-main",
    "name": "Main UPS",
    "type": "ups",
    "poller": "nut",
    "host": "192.168.1.10",
    "port": 3493,
    "enabled": true,
    "connection_config": {},
    "model": "SmartUPS 1500",
    "firmware": "1.0.0",
    "serial": "ABC123",
    "manufacturer": "APC",
    "last_seen": "2026-05-27T10:00:00Z"
  }
]
```

#### Get Device

```http
GET /api/devices/{device_id}
```

Returns `404` if the device does not exist.

---

### ⚡ Energy

```http
GET /api/energy
```

Returns cumulative kWh totals per device. Requires `energy` in `ENABLED_EXPORTERS`.

**Response:**

```json
[
  {
    "device_id": "ups-main",
    "kwh_total": 12.34,
    "cost_total": 1.85,
    "currency": "USD"
  }
]
```

---

### ▶️ Trigger Status

```http
GET /api/trigger/status
```

**Response:**

```json
{ "status": "idle", "message": "No poll in progress." }
```

---

### 🔍 Diagnostics

```http
GET /api/diagnostics
```

Returns last-poll diagnostics from the scheduler's shared state (device counts, errors, timing).

---

## 🔒 Protected Endpoints

All protected endpoints require `X-Api-Key` when `API_KEY` is set.

### ▶️ Trigger Manual Poll

```http
POST /api/trigger
X-Api-Key: <key>
```

**Response (`202 Accepted`):**

```json
{ "status": "accepted", "message": "Poll trigger queued." }
```

Returns `409 Conflict` if a poll is already in progress.

---

### ⚙️ Configuration

#### Get Runtime Config

```http
GET /api/config
```

**Response:**

```json
{
  "poll_interval_minutes": 5,
  "enabled_exporters": ["sqlite"],
  "scanning_disabled": false,
  "scheduler_paused": false,
  "nut_host": "192.168.1.10",
  "nut_port": 3493
}
```

#### Update Runtime Config

```http
PUT /api/config
X-Api-Key: <key>
Content-Type: application/json

{
  "poll_interval_minutes": 10,
  "enabled_exporters": ["sqlite", "prometheus"],
  "scanning_disabled": false,
  "scheduler_paused": false,
  "nut_host": "192.168.1.10",
  "nut_port": 3493
}
```

Changes take effect on the next poll cycle without a container restart.

---

### 🔔 Alerts

#### Get Alert Configuration

```http
GET /api/alerts
```

#### Update Alert Configuration

```http
PUT /api/alerts
X-Api-Key: <key>
Content-Type: application/json

{
  "providers": [
    {
      "type": "webhook",
      "enabled": true,
      "url": "https://hooks.example.com/argus",
      "min_severity": "medium"
    }
  ]
}
```

#### Test Alert Notification

```http
POST /api/alerts/test
X-Api-Key: <key>
```

Sends a test notification through all enabled providers.

---

### 🖥️ Devices (write)

#### Add Device

```http
POST /api/devices
X-Api-Key: <key>
Content-Type: application/json

{
  "id": "pdu-rack1",
  "name": "Rack 1 PDU",
  "type": "pdu",
  "poller": "snmp",
  "host": "192.168.1.20",
  "port": 161,
  "enabled": true,
  "connection_config": { "community": "public" }
}
```

Returns `409 Conflict` if the device ID already exists.

#### Update Device

```http
PUT /api/devices/{device_id}
X-Api-Key: <key>
Content-Type: application/json
```

#### Delete Device

```http
DELETE /api/devices/{device_id}
X-Api-Key: <key>
```

Returns `404` if not found.

#### Replace All Devices

```http
PUT /api/devices
X-Api-Key: <key>
Content-Type: application/json

[ { "id": "...", ... } ]
```

---

## ⚠️ Error Responses

| Status | Meaning |
| --- | --- |
| `400 Bad Request` | Invalid request body or parameters |
| `401 Unauthorized` | Missing or invalid `X-Api-Key` |
| `404 Not Found` | Resource does not exist |
| `409 Conflict` | Resource already exists (device) or poll in progress |
| `413 Request Entity Too Large` | Body exceeds 1 MB |
| `422 Unprocessable Entity` | Pydantic validation failed |
| `429 Too Many Requests` | Rate limit exceeded |
| `503 Service Unavailable` | SQLite database not reachable |
