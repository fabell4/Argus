---
layout: default
title: "Security Guide"
---

# 🔒 Security Guide

Argus implements multiple layers of security for production deployments. This guide covers
security features, configuration best practices, and hardening recommendations.

---

## 🛡️ Security Features

### 🔑 API Key Authentication

**Purpose:** Protect write endpoints from unauthorized access.

**Implementation:**

- Optional `API_KEY` environment variable
- **32-character minimum** enforced at startup (application exits if too short)
- Timing-safe comparison using `secrets.compare_digest()` to prevent timing attacks
- `X-Api-Key` header required on all protected endpoints

**Protected Endpoints:**

- `POST /api/trigger` — Manual poll trigger
- `PUT /api/config` — Configuration updates
- `PUT /api/alerts` — Alert configuration
- `POST /api/alerts/test` — Test alert notifications
- `POST /api/devices` — Add device
- `PUT /api/devices` — Replace device list
- `PUT /api/devices/{id}` — Update device
- `DELETE /api/devices/{id}` — Remove device

**Public Endpoints:** (no authentication required)

- `GET /api/health` — Health check
- `GET /api/snapshots` — Power snapshot history
- `GET /api/events` — Power event history
- `GET /api/devices` — Device list
- `GET /api/energy` — Energy totals
- `GET /api/config` — Current runtime configuration
- `GET /api/alerts` — Alert configuration
- `GET /api/trigger/status` — Poll status
- `GET /api/diagnostics` — Last-poll diagnostics

**Generate a Secure Key:**

```bash
# Recommended
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# Alternative
openssl rand -hex 32
```

**Startup validation failure message:**

```text
ERROR: API_KEY must be at least 32 characters long
Suggestion: Generate a secure key with:
  python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

---

### 🚦 Rate Limiting

**Purpose:** Prevent abuse and DoS via request flooding.

**Implementation:**

- Per-API-key sliding window rate limiting
- **Default:** 60 requests per 60-second window (configurable via `RATE_LIMIT_PER_MINUTE`)
- Applies to all protected endpoints
- Returns `429 Too Many Requests` with `Retry-After` header

---

### 🛡️ SSRF Protection on Alert URLs

**Purpose:** Prevent Server-Side Request Forgery through alert provider URLs.

**Implementation:**

- All alert provider URLs are validated at configuration time
- Only `https://` scheme is accepted — `http://` is rejected
- Validation is enforced at both the Pydantic model layer and runtime

**Rejected configuration:**

```bash
WEBHOOK_URL=http://internal-host/secret   # rejected — not HTTPS
GOTIFY_URL=http://gotify.example.com      # rejected — not HTTPS
```

---

### 🔐 Security Headers

Every API response includes the following headers:

| Header | Value |
| --- | --- |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; …` |

---

### 📏 Request Size Limits

All requests are limited to **1 MB**. Requests with a `Content-Length` exceeding this return
`413 Request Entity Too Large` immediately, before the body is read.

---

### 🌐 CORS Restrictions

The API restricts cross-origin requests to explicitly allowed origins configured via
`ALLOWED_ORIGINS`. The default allows only local development origins.

**Production example:**

```bash
ALLOWED_ORIGINS=https://argus.example.com
```

---

## ✅ Production Hardening Checklist

- [ ] Set `API_KEY` to a randomly generated 32+ character secret
- [ ] Set `ALLOWED_ORIGINS` to your actual UI domain (not `*`)
- [ ] Set `APP_ENV=production`
- [ ] Use HTTPS in front of the API (reverse proxy with TLS)
- [ ] Set `API_HOST=127.0.0.1` and expose via reverse proxy rather than binding to `0.0.0.0`
- [ ] Restrict Docker port bindings (`127.0.0.1:8000:8000`)
- [ ] Use read-only filesystem mounts where possible
- [ ] Rotate `API_KEY` regularly
- [ ] Enable `ALERT_ON_DEVICE_OFFLINE` to detect monitoring gaps

---

## 🔐 Reverse Proxy with TLS (Nginx Example)

```nginx
server {
    listen 443 ssl http2;
    server_name argus.example.com;

    ssl_certificate     /etc/letsencrypt/live/argus.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/argus.example.com/privkey.pem;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name argus.example.com;
    return 301 https://$host$request_uri;
}
```

---

## 🔑 NUT Credential Security

NUT username and password (`NUT_USERNAME`, `NUT_PASSWORD`) are transmitted in plaintext over
the NUT TCP protocol. Mitigations:

- Keep NUT and Argus on the same private network or Docker bridge
- Use a dedicated read-only NUT user (`upsmon`) with minimal permissions
- Do not expose port 3493 to the public internet

**Minimal NUT `upsd.users` entry:**

```ini
[argus]
  password = <strong-random-password>
  upsmon primary
```

---

## 📡 SNMPv3 Security

For SNMP devices, prefer SNMPv3 with authentication and privacy encryption over the
default community-string-based v2c:

```bash
SNMP_VERSION=3
SNMP_V3_USERNAME=argus-monitor
SNMP_V3_AUTH_PROTOCOL=SHA          # stronger than MD5
SNMP_V3_AUTH_KEY=<strong-key>
SNMP_V3_PRIV_PROTOCOL=AES          # stronger than DES
SNMP_V3_PRIV_KEY=<strong-key>
```

Do not store these values in version-controlled files — use Docker secrets or a secrets manager.

---

## 📢 Reporting Vulnerabilities

Please report security vulnerabilities privately via the process described in
[SECURITY.md](https://github.com/fabell4/argus/blob/main/SECURITY.md).
