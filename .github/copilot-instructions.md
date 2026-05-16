# Copilot Instructions

## Project Overview
Argus is a local-first power monitoring application for UPS devices (via NUT), PDUs, and sensors
(via SNMP). It follows the same two-process architecture and module conventions as the Hermes project.

## Development Guidelines
- Use Python 3.12+ best practices and PEP 8 / ruff style
- Organize code into modules under the `src/` directory
- Place tests in the `tests/` directory
- Keep dependencies listed in `requirements.txt` and `requirements-dev.txt`
- Use virtual environment for dependency isolation
- TypeScript strict mode for all frontend code under `frontend/src/`

## Project Structure
- `src/` — Main application source code (scheduler + API)
- `src/models/` — PowerSnapshot, Device, PowerEvent dataclasses
- `src/exporters/` — SQLite, Prometheus, InfluxDB exporters
- `src/services/` — NUT/SNMP pollers, EventProcessor, AlertManager, AlertProviders, HealthServer
- `src/api/` — FastAPI app with auth, middleware, and routes
- `tests/` — Unit and integration tests
- `frontend/` — React 18 TypeScript SPA (Vite, recharts, framer-motion)
- `data/` — SQLite database and runtime config (git-ignored at runtime)
- `requirements.txt` — Runtime dependencies
- `requirements-dev.txt` — Dev/test dependencies
- `.env.example` — Example environment variables

## Architecture
- **Scheduler process**: `python -m src.main` — runs APScheduler, polls NUT/SNMP, dispatches to exporters
- **API process**: `uvicorn src.api.main:app` — serves REST API and React SPA
- Both processes share `data/` volume for SQLite and runtime config

## Release Policy
See `.github/instructions/release-policy.instructions.md` for full versioning and release rules.
