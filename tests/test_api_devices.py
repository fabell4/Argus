"""Tests for /api/devices CRUD endpoints."""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app, raise_server_exceptions=False)

_DEVICE: dict = {
    "id": "nut:ups@localhost",
    "name": "Main UPS",
    "type": "ups",
    "poller": "nut",
    "host": "localhost",
    "port": 3493,
    "enabled": True,
    "connection_config": {},
    "model": None,
    "firmware": None,
    "serial": None,
    "manufacturer": None,
    "last_seen": None,
}

# ---------------------------------------------------------------------------
# GET /api/devices/{device_id}
# ---------------------------------------------------------------------------


def test_get_device_returns_200_when_found() -> None:
    """Fetching an existing device returns 200 with the device payload."""
    with patch("src.api.routes.devices.device_registry.get_device", return_value=_DEVICE):
        resp = client.get("/api/devices/nut:ups@localhost")
    assert resp.status_code == 200
    assert resp.json()["id"] == "nut:ups@localhost"


def test_get_device_returns_404_when_not_found() -> None:
    """Fetching a non-existent device returns 404."""
    with patch("src.api.routes.devices.device_registry.get_device", return_value=None):
        resp = client.get("/api/devices/no-such-device")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/devices
# ---------------------------------------------------------------------------


def test_add_device_returns_201_when_new() -> None:
    """Adding a new device returns 201."""
    with (
        patch("src.api.routes.devices.device_registry.get_device", return_value=None),
        patch("src.api.routes.devices.device_registry.upsert_device"),
    ):
        resp = client.post("/api/devices", json=_DEVICE)
    assert resp.status_code == 201


def test_add_device_returns_409_when_already_exists() -> None:
    """Adding a device that already exists returns 409."""
    with patch("src.api.routes.devices.device_registry.get_device", return_value=_DEVICE):
        resp = client.post("/api/devices", json=_DEVICE)
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# PUT /api/devices (bulk replace)
# ---------------------------------------------------------------------------


def test_replace_devices_returns_200() -> None:
    """Replacing the device list returns 200."""
    with patch("src.api.routes.devices.device_registry.save_devices"):
        resp = client.put("/api/devices", json=[_DEVICE])
    assert resp.status_code == 200


def test_replace_devices_with_empty_list() -> None:
    """Replacing devices with an empty list clears the registry."""
    with patch("src.api.routes.devices.device_registry.save_devices") as mock_save:
        resp = client.put("/api/devices", json=[])
    assert resp.status_code == 200
    mock_save.assert_called_once_with([])


# ---------------------------------------------------------------------------
# PUT /api/devices/{device_id}
# ---------------------------------------------------------------------------


def test_update_device_returns_200() -> None:
    """Updating an existing device returns 200 with the updated payload."""
    with (
        patch("src.api.routes.devices.device_registry.get_device", return_value=_DEVICE),
        patch("src.api.routes.devices.device_registry.upsert_device"),
    ):
        resp = client.put("/api/devices/nut:ups@localhost", json=_DEVICE)
    assert resp.status_code == 200
    assert resp.json()["id"] == "nut:ups@localhost"


def test_update_device_returns_404_when_missing() -> None:
    """Updating a non-existent device returns 404."""
    updated = {**_DEVICE, "id": "nut:missing@localhost"}
    with patch("src.api.routes.devices.device_registry.get_device", return_value=None):
        resp = client.put("/api/devices/nut:missing@localhost", json=updated)
    assert resp.status_code == 404


def test_update_device_returns_400_on_id_mismatch() -> None:
    """Updating with a body ID that doesn't match the path parameter returns 400."""
    mismatched = {**_DEVICE, "id": "different-id"}
    with patch("src.api.routes.devices.device_registry.get_device", return_value=_DEVICE):
        resp = client.put("/api/devices/nut:ups@localhost", json=mismatched)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/devices/{device_id}
# ---------------------------------------------------------------------------


def test_delete_device_returns_204_when_found() -> None:
    """Deleting an existing device returns 204."""
    with patch("src.api.routes.devices.device_registry.remove_device", return_value=True):
        resp = client.delete("/api/devices/nut:ups@localhost")
    assert resp.status_code == 204


def test_delete_device_returns_404_when_missing() -> None:
    """Deleting a non-existent device returns 404."""
    with patch("src.api.routes.devices.device_registry.remove_device", return_value=False):
        resp = client.delete("/api/devices/no-such-device")
    assert resp.status_code == 404
