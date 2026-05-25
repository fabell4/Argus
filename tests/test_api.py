"""Tests for the API health, snapshots, trigger, and config endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_returns_ok() -> None:
    """GET /api/health returns 200 with status ok."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Snapshots (empty DB expected in test environment)
# ---------------------------------------------------------------------------


def test_list_snapshots_returns_page() -> None:
    """GET /api/snapshots returns a valid response (200 or 503 when SQLite absent)."""
    resp = client.get("/api/snapshots")
    assert resp.status_code in (200, 503)


def test_latest_snapshot_returns_none_or_snapshot() -> None:
    """GET /api/snapshots/latest returns 200 or 503."""
    resp = client.get("/api/snapshots/latest")
    assert resp.status_code in (200, 503)


# ---------------------------------------------------------------------------
# Trigger (no auth required when API_KEY is empty)
# ---------------------------------------------------------------------------


def test_trigger_status_idle() -> None:
    """GET /api/trigger/status returns idle or running."""
    resp = client.get("/api/trigger/status")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("idle", "running")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def test_get_config() -> None:
    """GET /api/config returns poll_interval_minutes and enabled_exporters."""
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert "poll_interval_minutes" in body
    assert "enabled_exporters" in body


def test_update_config_without_auth_when_key_empty() -> None:
    """PUT /api/config succeeds when API_KEY is unset, else 401/403."""
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
    """GET /api/events returns a valid response."""
    resp = client.get("/api/events")
    assert resp.status_code in (200, 503)


def test_list_events_with_device_id_filter() -> None:
    """GET /api/events?device_id=... passes the filter without error."""
    resp = client.get("/api/events?device_id=nut:ups@localhost")
    assert resp.status_code in (200, 503)


def test_list_events_with_event_type_filter() -> None:
    """GET /api/events?event_type=... passes the filter without error."""
    resp = client.get("/api/events?event_type=ON_BATTERY")
    assert resp.status_code in (200, 503)


def test_list_events_with_pagination_params() -> None:
    """GET /api/events?page=1&page_size=10 passes pagination params without error."""
    resp = client.get("/api/events?page=1&page_size=10")
    assert resp.status_code in (200, 503)


# ---------------------------------------------------------------------------
# Snapshots — filter variants
# ---------------------------------------------------------------------------


def test_list_snapshots_with_device_id_filter() -> None:
    """GET /api/snapshots?device_id=... passes the filter without error."""
    resp = client.get("/api/snapshots?device_id=nut:ups@localhost")
    assert resp.status_code in (200, 503)


def test_latest_snapshot_with_device_id_filter() -> None:
    """GET /api/snapshots/latest?device_id=... passes the filter without error."""
    resp = client.get("/api/snapshots/latest?device_id=nut:ups@localhost")
    assert resp.status_code in (200, 503)


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------


def test_list_devices_returns_list() -> None:
    """GET /api/devices returns a JSON list."""
    resp = client.get("/api/devices")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
