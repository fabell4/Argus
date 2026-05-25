"""Shared device registry — backed by data/devices.json.

Both the scheduler (src/main.py) and the API (src/api/routes/devices.py) use
this module so they share a single source of truth for the device list.
Writes use atomic rename to prevent partial reads.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import Any

_LOG = logging.getLogger(__name__)
_DEVICES_FILE = os.path.join("data", "devices.json")


# ---------------------------------------------------------------------------
# Low-level I/O
# ---------------------------------------------------------------------------


def _load_raw() -> list[dict[str, Any]]:
    if not os.path.exists(_DEVICES_FILE):
        return []
    try:
        with open(_DEVICES_FILE, encoding="utf-8") as fh:
            data: list[dict[str, Any]] = json.load(fh)
            return data
    except (json.JSONDecodeError, OSError):
        _LOG.warning("devices.json is corrupt or unreadable; returning empty list.")
        return []


def _save_raw(devices: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(_DEVICES_FILE), exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        dir=os.path.dirname(_DEVICES_FILE),
        delete=False,
        suffix=".tmp",
        encoding="utf-8",
    ) as tmp:
        json.dump(devices, tmp, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, _DEVICES_FILE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_devices() -> list[dict[str, Any]]:
    """Return the full device list."""
    return _load_raw()


def save_devices(devices: list[dict[str, Any]]) -> None:
    """Atomically replace the device list."""
    _save_raw(devices)


def get_device(device_id: str) -> dict[str, Any] | None:
    """Return a single device by ID, or None if not found."""
    for device in _load_raw():
        if device.get("id") == device_id:
            return device
    return None


def upsert_device(device: dict[str, Any]) -> None:
    """Insert or update a device by ID.

    If the device already exists, only non-None fields in *device* overwrite
    the stored values so that partial metadata updates don't erase existing data.
    """
    devices = _load_raw()
    device_id = device.get("id")
    for i, existing in enumerate(devices):
        if existing.get("id") == device_id:
            # Merge: keep existing values for keys absent/None in the update
            merged = {**existing}
            for k, v in device.items():
                if v is not None:
                    merged[k] = v
            devices[i] = merged
            _save_raw(devices)
            return
    # Not found — insert as new entry
    devices.append(device)
    _save_raw(devices)


def remove_device(device_id: str) -> bool:
    """Remove a device by ID.  Returns True if found and removed."""
    devices = _load_raw()
    updated = [d for d in devices if d.get("id") != device_id]
    if len(updated) == len(devices):
        return False
    _save_raw(updated)
    return True
