"""Tests for EventProcessor."""
from __future__ import annotations

from datetime import datetime, timezone

from src.constants import EventType
from src.models.power_snapshot import PowerSnapshot
from src.services.event_processor import EventProcessor


def _snap(**kwargs: object) -> PowerSnapshot:
    defaults = {
        "timestamp": datetime.now(timezone.utc),
        "device_id": "nut:ups@localhost",
        "device_type": "ups",
    }
    defaults.update(kwargs)
    return PowerSnapshot(**defaults)  # type: ignore[arg-type]


def test_no_events_on_first_snapshot() -> None:
    proc = EventProcessor()
    events = proc.process(_snap(ups_status="OL"))
    assert events == []


def test_on_battery_event_emitted() -> None:
    proc = EventProcessor()
    proc.process(_snap(ups_status="OL"))
    events = proc.process(_snap(ups_status="OB"))
    assert any(e.event_type == EventType.ON_BATTERY for e in events)


def test_power_restored_event_emitted() -> None:
    proc = EventProcessor()
    proc.process(_snap(ups_status="OL"))
    proc.process(_snap(ups_status="OB"))
    events = proc.process(_snap(ups_status="OL"))
    assert any(e.event_type == EventType.POWER_RESTORED for e in events)


def test_battery_low_event_emitted() -> None:
    proc = EventProcessor()
    proc.process(_snap(battery_percent=80.0))
    events = proc.process(_snap(battery_percent=15.0))
    assert any(e.event_type == EventType.BATTERY_LOW for e in events)


def test_no_battery_low_if_already_low() -> None:
    proc = EventProcessor()
    proc.process(_snap(battery_percent=15.0))
    events = proc.process(_snap(battery_percent=10.0))
    # already below threshold — no new event
    assert not any(e.event_type == EventType.BATTERY_LOW for e in events)
