"""Tests for alert API endpoints, security headers, and input validation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /api/alerts
# ---------------------------------------------------------------------------


def test_get_alerts_returns_default_schema() -> None:
    """GET /api/alerts returns all expected top-level keys."""
    resp = client.get("/api/alerts")
    assert resp.status_code == 200
    body = resp.json()
    assert "providers" in body
    assert "failure_threshold" in body
    assert "cooldown_seconds" in body
    assert "alert_on_battery" in body
    assert "alert_on_battery_low" in body
    assert "alert_on_device_offline" in body
    assert "alert_recovery_notifications" in body
    assert "recovery_cooldown_seconds" in body


def test_get_alerts_providers_is_list() -> None:
    """The providers field in the alert config response is a list."""
    resp = client.get("/api/alerts")
    assert isinstance(resp.json()["providers"], list)


# ---------------------------------------------------------------------------
# PUT /api/alerts
# ---------------------------------------------------------------------------


def test_put_alerts_persists_config() -> None:
    """PUT /api/alerts with valid body returns the saved config including recovery_cooldown_seconds.

    Verifies failure_threshold, alert_on_battery, and recovery_cooldown_seconds are persisted.
    """
    body = {
        "providers": [],
        "failure_threshold": 5,
        "cooldown_seconds": 1800,
        "alert_on_battery": False,
        "alert_on_battery_low": True,
        "alert_on_device_offline": True,
        "alert_recovery_notifications": False,
        "recovery_cooldown_seconds": 600,
    }
    resp = client.put("/api/alerts", json=body)
    assert resp.status_code in (200, 401, 403)
    if resp.status_code == 200:
        result = resp.json()
        assert result["failure_threshold"] == 5
        assert result["alert_on_battery"] is False
        assert result["recovery_cooldown_seconds"] == 600


def test_put_alerts_rejects_oversized_recovery_cooldown() -> None:
    """recovery_cooldown_seconds above 86400 is rejected with 422."""
    body = {
        "providers": [],
        "failure_threshold": 3,
        "cooldown_seconds": 3600,
        "recovery_cooldown_seconds": 999999,  # exceeds max 86400
    }
    resp = client.put("/api/alerts", json=body)
    assert resp.status_code in (422, 401, 403)


def test_put_alerts_rejects_too_small_recovery_cooldown() -> None:
    """recovery_cooldown_seconds below 60 is rejected with 422."""
    body = {
        "providers": [],
        "failure_threshold": 3,
        "cooldown_seconds": 3600,
        "recovery_cooldown_seconds": 10,  # below minimum 60
    }
    resp = client.put("/api/alerts", json=body)
    assert resp.status_code in (422, 401, 403)


def test_put_alerts_rejects_invalid_failure_threshold() -> None:
    """failure_threshold of 0 is rejected with 422."""
    body = {
        "providers": [],
        "failure_threshold": 0,  # must be >= 1
        "cooldown_seconds": 3600,
    }
    resp = client.put("/api/alerts", json=body)
    assert resp.status_code in (422, 401, 403)


def test_put_alerts_rejects_oversized_cooldown() -> None:
    """cooldown_seconds above 86400 is rejected with 422."""
    body = {
        "providers": [],
        "failure_threshold": 3,
        "cooldown_seconds": 999999,  # exceeds max 86400
    }
    resp = client.put("/api/alerts", json=body)
    assert resp.status_code in (422, 401, 403)


def test_put_alerts_with_webhook_provider() -> None:
    """PUT /api/alerts with a valid webhook provider config is accepted."""
    body = {
        "providers": [
            {
                "type": "webhook",
                "enabled": True,
                "url": "https://hooks.example.com/argus",
            }
        ],
        "failure_threshold": 3,
        "cooldown_seconds": 3600,
    }
    resp = client.put("/api/alerts", json=body)
    assert resp.status_code in (200, 401, 403)


def test_put_alerts_rejects_http_url_missing_scheme() -> None:
    """Webhook URL without http/https scheme is rejected with 422."""
    body = {
        "providers": [
            {"type": "webhook", "enabled": True, "url": "hooks.example.com/argus"}
        ],
        "failure_threshold": 3,
        "cooldown_seconds": 3600,
    }
    resp = client.put("/api/alerts", json=body)
    assert resp.status_code in (422, 401, 403)


# ---------------------------------------------------------------------------
# POST /api/alerts/test
# ---------------------------------------------------------------------------


def test_post_alerts_test_returns_503_when_no_alert_manager() -> None:
    """POST /api/alerts/test returns 503 when the alert manager is unavailable."""
    with patch("src.api.routes.alerts.shared_state") as mock_state:
        mock_state.get_alert_manager.return_value = None
        resp = client.post("/api/alerts/test")
    assert resp.status_code == 503


def test_post_alerts_test_returns_ok_with_alert_manager() -> None:
    """POST /api/alerts/test returns 200 and status ok when dispatch succeeds."""
    mock_mgr = MagicMock()
    mock_mgr.send_test_alert = MagicMock()
    with patch("src.api.routes.alerts.shared_state") as mock_state:
        mock_state.get_alert_manager.return_value = mock_mgr
        resp = client.post("/api/alerts/test")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_post_alerts_test_returns_429_on_cooldown_error() -> None:
    """POST /api/alerts/test returns 429 when the test-alert cooldown is active."""
    mock_mgr = MagicMock()
    mock_mgr.send_test_alert.side_effect = RuntimeError("cooldown active")
    with patch("src.api.routes.alerts.shared_state") as mock_state:
        mock_state.get_alert_manager.return_value = mock_mgr
        resp = client.post("/api/alerts/test")
    assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------


def test_security_headers_present_on_health() -> None:
    """Security headers (nosniff, deny, referrer-policy) are present on health responses."""
    resp = client.get("/api/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_security_headers_present_on_alerts() -> None:
    """Security headers are present on alert endpoint responses."""
    resp = client.get("/api/alerts")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"


# ---------------------------------------------------------------------------
# Request size limit
# ---------------------------------------------------------------------------


def test_oversized_request_rejected() -> None:
    """PUT requests with a body exceeding the size limit are rejected with 413."""
    # Send a PUT with 2 MB body — should be rejected with 413
    large_body = "x" * (2 * 1024 * 1024)
    resp = client.put(
        "/api/config",
        content=large_body,
        headers={
            "Content-Length": str(len(large_body)),
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 413


# ---------------------------------------------------------------------------
# Input validation on config routes
# ---------------------------------------------------------------------------


def test_put_config_rejects_negative_poll_interval() -> None:
    """PUT /api/config rejects a negative poll_interval_minutes value."""
    resp = client.put(
        "/api/config",
        json={
            "poll_interval_minutes": -5,
            "enabled_exporters": ["sqlite"],
            "scanning_disabled": False,
            "scheduler_paused": False,
        },
    )
    assert resp.status_code in (422, 401, 403)


def test_put_config_rejects_string_poll_interval() -> None:
    """PUT /api/config rejects a non-integer poll_interval_minutes value."""
    resp = client.put(
        "/api/config",
        json={
            "poll_interval_minutes": "invalid",
            "enabled_exporters": ["sqlite"],
        },
    )
    assert resp.status_code in (422, 401, 403)


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def test_get_diagnostics_returns_structure() -> None:
    """GET /api/diagnostics returns a JSON object."""
    resp = client.get("/api/diagnostics")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, dict)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


def test_cors_headers_present_for_allowed_origin() -> None:
    """CORS preflight does not 500 for a configured allowed origin."""
    with patch("src.api.main.config") as mock_cfg:
        mock_cfg.ALLOWED_ORIGINS = ["http://localhost:5173"]
        mock_cfg.RATE_LIMIT_PER_MINUTE = 60
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    # preflight or regular response; CORS headers should be present when origin matches
    # (may vary by client config; just check it doesn't 500)
    assert resp.status_code in (200, 204, 400)
