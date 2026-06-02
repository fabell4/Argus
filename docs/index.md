---
layout: home
title: "Argus Documentation"
description: "Self-hosted power monitoring for UPS devices, PDUs, and sensors with full observability stack integration"
show_header: false

hero_title: "Argus Docs"
hero_subtitle: "Self-hosted power monitoring for UPS devices (NUT), PDUs, and sensors (SNMP) with multi-destination export, event-driven alerting, and full observability stack integration."
hero_cta:
  - label: "Get Started"
    url: /getting-started
    primary: true
  - label: "View on GitHub"
    url: https://github.com/fabell4/argus

quick_links:
  - title: "Getting Started"
    url: /getting-started
    icon: "🚀"
    description: "Deploy with Docker, configure NUT/SNMP, and run your first poll cycle."
  - title: "Architecture"
    url: /architecture
    icon: "🏗️"
    description: "System design, data flow, and two-container deployment topology."
  - title: "API Reference"
    url: /api-reference
    icon: "🔌"
    description: "REST endpoints, authentication, and request/response examples."
  - title: "Alert Configuration"
    url: /alerts
    icon: "🔔"
    description: "Webhook, Gotify, ntfy, and Apprise notification setup."
  - title: "Security Guide"
    url: /security
    icon: "🔐"
    description: "API key auth, rate limiting, SSRF protection, and best practices."
  - title: "Runbook"
    url: /runbook
    icon: "📖"
    description: "Operational guide for diagnosing and resolving production issues."
---

## Quick Start

```bash
# 1. Pull the compose file
curl -o docker-compose.yml \
  https://raw.githubusercontent.com/fabell4/argus/main/docker-compose.yml

# 2. Create your .env
curl -o .env \
  https://raw.githubusercontent.com/fabell4/argus/main/.env.example

# 3. Edit .env — set NUT_HOST to your NUT daemon address
# 4. Start
docker compose up -d

# 5. Access the UI
open http://localhost:8000
```

---

## Key Features

| Feature | Details |
| --- | --- |
| **Device Support** | UPS via NUT, PDUs and sensors via SNMP |
| **Auto Discovery** | Automatically discovers all UPS units from a NUT daemon |
| **Export Destinations** | SQLite, Prometheus, InfluxDB, Loki, CSV, energy accumulator |
| **Alert Providers** | Webhook, Gotify, ntfy, Apprise (100+ services) |
| **Security** | API key auth, per-key rate limiting, SSRF protection |
| **Frontend** | React + Vite UI with real-time charts and device dashboards |

See [Getting Started](/getting-started) for the full environment variable reference.
