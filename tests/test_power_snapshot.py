"""Tests for src/models/power_snapshot.py."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.models.power_snapshot import PowerSnapshot


def _make(**kwargs: object) -> PowerSnapshot:
    defaults = {
        "timestamp": datetime.now(timezone.utc),
        "device_id": "nut:ups@localhost",
        "device_type": "ups",
    }
    defaults.update(kwargs)
    return PowerSnapshot(**defaults)  # type: ignore[arg-type]


def test_valid_snapshot() -> None:
    snap = _make(load_percent=50.0, battery_percent=80.0, power_watts=100.0)
    assert snap.device_id == "nut:ups@localhost"
    assert snap.load_percent == 50.0


def test_naive_timestamp_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _make(timestamp=datetime.now())


def test_empty_device_id_rejected() -> None:
    with pytest.raises(ValueError, match="device_id"):
        _make(device_id="")


def test_invalid_load_percent_rejected() -> None:
    with pytest.raises(ValueError, match="load_percent"):
        _make(load_percent=150.0)


def test_negative_power_watts_rejected() -> None:
    with pytest.raises(ValueError, match="power_watts"):
        _make(power_watts=-1.0)


def test_to_dict_roundtrip() -> None:
    snap = _make(power_watts=250.0, battery_percent=75.0)
    d = snap.to_dict()
    assert d["power_watts"] == 250.0
    assert d["battery_percent"] == 75.0
    assert "timestamp" in d
