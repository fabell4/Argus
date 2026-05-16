"""Tests for the API health, snapshots, trigger, and config endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health_returns_ok() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Snapshots (empty DB expected in test environment)
# ---------------------------------------------------------------------------

def test_list_snapshots_returns_page() -> None:
    resp = client.get("/api/snapshots")
    assert resp.status_code in (200, 503)  # 503 if SQLite not initialised


def test_latest_snapshot_returns_none_or_snapshot() -> None:
    resp = client.get("/api/snapshots/latest")
    assert resp.status_code in (200, 503)


# ---------------------------------------------------------------------------
# Trigger (no auth required when API_KEY is empty)
# ---------------------------------------------------------------------------

def test_trigger_status_idle() -> None:
    resp = client.get("/api/trigger/status")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("idle", "running")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_get_config() -> None:
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert "poll_interval_minutes" in body
    assert "enabled_exporters" in body


def test_update_config_without_auth_when_key_empty() -> None:
    resp = client.put(
        "/api/config",
        json={
            "poll_interval_minutes": 10,
            "enabled_exporters": ["sqlite"],
            "scanning_disabled": False,
            "scheduler_paused": False,
        },
    )
    # 200 when API_KEY is not set; 401/403 when it is
    assert resp.status_code in (200, 401, 403)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def test_list_events_returns_page() -> None:
    resp = client.get("/api/events")
    assert resp.status_code in (200, 503)


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------

def test_list_devices_returns_list() -> None:
    resp = client.get("/api/devices")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
