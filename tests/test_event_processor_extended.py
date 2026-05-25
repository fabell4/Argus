"""Extended tests for EventProcessor — all event types, multi-device, and edge cases."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.constants import EventType
from src.models.power_snapshot import PowerSnapshot
from src.services.event_processor import EventProcessor


def _snap(**kwargs: object) -> PowerSnapshot:
    defaults: dict[str, object] = {
        "timestamp": datetime.now(timezone.utc),
        "device_id": "nut:ups@localhost",
        "device_type": "ups",
    }
    defaults.update(kwargs)
    return PowerSnapshot(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SHUTDOWN_INITIATED
# ---------------------------------------------------------------------------


def test_shutdown_initiated_when_on_battery_and_below_floor() -> None:
    """SHUTDOWN_INITIATED is emitted when on battery and battery is below the floor threshold."""
    proc = EventProcessor()
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 10
        mock_cfg.THRESHOLD_LOAD_PERCENT = 90
        mock_cfg.THRESHOLD_TEMPERATURE_C = 50
        proc.process(_snap(ups_status="OB", battery_percent=50.0))
        events = proc.process(_snap(ups_status="OB", battery_percent=8.0))
    assert any(e.event_type == EventType.SHUTDOWN_INITIATED for e in events)


def test_shutdown_initiated_not_fired_twice() -> None:
    """SHUTDOWN_INITIATED is only fired once per battery-low event.

    Subsequent polls while still below the floor must not repeat it.
    """
    proc = EventProcessor()
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 10
        mock_cfg.THRESHOLD_LOAD_PERCENT = 90
        mock_cfg.THRESHOLD_TEMPERATURE_C = 50
        proc.process(_snap(ups_status="OB", battery_percent=50.0))
        proc.process(_snap(ups_status="OB", battery_percent=8.0))  # fires once
        events = proc.process(_snap(ups_status="OB", battery_percent=5.0))
    assert not any(e.event_type == EventType.SHUTDOWN_INITIATED for e in events)


def test_shutdown_not_initiated_when_on_mains() -> None:
    """SHUTDOWN_INITIATED is never emitted when the device is on mains (OL) power."""
    proc = EventProcessor()
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 10
        mock_cfg.THRESHOLD_LOAD_PERCENT = 90
        mock_cfg.THRESHOLD_TEMPERATURE_C = 50
        proc.process(_snap(ups_status="OL", battery_percent=50.0))
        events = proc.process(_snap(ups_status="OL", battery_percent=5.0))
    assert not any(e.event_type == EventType.SHUTDOWN_INITIATED for e in events)


def test_shutdown_flag_cleared_on_power_restored() -> None:
    """Shutdown-fired flag is cleared on power restore so the event can fire again next time."""
    proc = EventProcessor()
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 10
        mock_cfg.THRESHOLD_LOAD_PERCENT = 90
        mock_cfg.THRESHOLD_TEMPERATURE_C = 50
        proc.process(_snap(ups_status="OB", battery_percent=50.0))
        proc.process(_snap(ups_status="OB", battery_percent=5.0))  # shutdown fired
        proc.process(_snap(ups_status="OL", battery_percent=90.0))  # power restored
        # Now drop battery low again — shutdown should fire again
        events = proc.process(_snap(ups_status="OB", battery_percent=3.0))
    assert any(e.event_type == EventType.SHUTDOWN_INITIATED for e in events)


# ---------------------------------------------------------------------------
# THRESHOLD_CROSSED
# ---------------------------------------------------------------------------


def test_threshold_crossed_on_load_spike() -> None:
    """THRESHOLD_CROSSED is emitted when load_percent crosses the configured threshold."""
    proc = EventProcessor()
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 5
        mock_cfg.THRESHOLD_LOAD_PERCENT = 80
        mock_cfg.THRESHOLD_TEMPERATURE_C = 50
        proc.process(_snap(load_percent=60.0))
        events = proc.process(_snap(load_percent=85.0))
    assert any(e.event_type == EventType.THRESHOLD_CROSSED for e in events)


def test_threshold_crossed_not_re_emitted_when_already_high() -> None:
    """THRESHOLD_CROSSED is not re-emitted when load was already above threshold
    on the previous poll.
    """
    proc = EventProcessor()
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 5
        mock_cfg.THRESHOLD_LOAD_PERCENT = 80
        mock_cfg.THRESHOLD_TEMPERATURE_C = 50
        proc.process(_snap(load_percent=85.0))
        events = proc.process(_snap(load_percent=90.0))
    assert not any(e.event_type == EventType.THRESHOLD_CROSSED for e in events)


# ---------------------------------------------------------------------------
# DEVICE_OFFLINE / DEVICE_ONLINE
# ---------------------------------------------------------------------------


def test_device_offline_after_missed_polls() -> None:
    """DEVICE_OFFLINE is emitted after the configured number of consecutive missed polls."""
    proc = EventProcessor()
    device_id = "nut:ups@host"
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.DEVICE_OFFLINE_MISSED_POLLS = 2
        proc.record_missed_poll(device_id)
        events = proc.record_missed_poll(device_id)
    assert any(e.event_type == EventType.DEVICE_OFFLINE for e in events)


def test_device_offline_not_fired_before_threshold() -> None:
    """DEVICE_OFFLINE is not emitted when missed poll count is below the configured threshold."""
    proc = EventProcessor()
    device_id = "nut:ups@host"
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.DEVICE_OFFLINE_MISSED_POLLS = 3
        events = proc.record_missed_poll(device_id)
    assert not any(e.event_type == EventType.DEVICE_OFFLINE for e in events)


def test_device_offline_not_fired_twice() -> None:
    """DEVICE_OFFLINE is only fired once per offline incident.

    Subsequent missed polls after the device is already offline must not re-emit it.
    """
    proc = EventProcessor()
    device_id = "nut:ups@host"
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.DEVICE_OFFLINE_MISSED_POLLS = 1
        proc.record_missed_poll(device_id)  # fires offline
        events = proc.record_missed_poll(device_id)  # must NOT fire again
    assert not any(e.event_type == EventType.DEVICE_OFFLINE for e in events)


def test_device_online_event_on_recovery_after_offline() -> None:
    """DEVICE_ONLINE is emitted when a successful poll is received after the device went offline."""
    proc = EventProcessor()
    device_id = "nut:ups@host"
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.DEVICE_OFFLINE_MISSED_POLLS = 1
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 5
        mock_cfg.THRESHOLD_LOAD_PERCENT = 90
        mock_cfg.THRESHOLD_TEMPERATURE_C = 50
        proc.record_missed_poll(device_id)  # device goes offline
        events = proc.process(_snap(device_id=device_id))  # device recovers
    assert any(e.event_type == EventType.DEVICE_ONLINE for e in events)


def test_missed_poll_counter_resets_after_recovery() -> None:
    """Missed-poll counter resets to zero after a successful poll.

    This prevents false DEVICE_OFFLINE detection after a brief recovery.
    """
    proc = EventProcessor()
    device_id = "nut:ups@host"
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.DEVICE_OFFLINE_MISSED_POLLS = 3
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 5
        mock_cfg.THRESHOLD_LOAD_PERCENT = 90
        mock_cfg.THRESHOLD_TEMPERATURE_C = 50
        proc.record_missed_poll(device_id)
        proc.record_missed_poll(device_id)
        proc.process(_snap(device_id=device_id))  # recovery resets counter
        events = proc.record_missed_poll(device_id)  # 1 missed — should not go offline
    assert not any(e.event_type == EventType.DEVICE_OFFLINE for e in events)


# ---------------------------------------------------------------------------
# Multi-device isolation
# ---------------------------------------------------------------------------


def test_two_devices_tracked_independently() -> None:
    """Events for one device do not affect the state of another device.

    Both devices are tracked independently by the same EventProcessor instance.
    """
    proc = EventProcessor()
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 5
        mock_cfg.THRESHOLD_LOAD_PERCENT = 90
        mock_cfg.THRESHOLD_TEMPERATURE_C = 50
        proc.process(_snap(device_id="dev-a", ups_status="OL"))
        proc.process(_snap(device_id="dev-b", ups_status="OL"))
        # Only dev-a goes on battery
        events = proc.process(_snap(device_id="dev-a", ups_status="OB"))
    assert all(
        e.device_id == "dev-a" for e in events if e.event_type == EventType.ON_BATTERY
    )


def test_battery_low_isolated_per_device() -> None:
    """BATTERY_LOW events are isolated per device and do not cross-contaminate device state."""
    proc = EventProcessor()
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 5
        mock_cfg.THRESHOLD_LOAD_PERCENT = 90
        mock_cfg.THRESHOLD_TEMPERATURE_C = 50
        proc.process(_snap(device_id="dev-a", battery_percent=80.0))
        proc.process(_snap(device_id="dev-b", battery_percent=80.0))
        events_a = proc.process(_snap(device_id="dev-a", battery_percent=10.0))
        events_b = proc.process(_snap(device_id="dev-b", battery_percent=70.0))
    assert any(e.event_type == EventType.BATTERY_LOW for e in events_a)
    assert not any(e.event_type == EventType.BATTERY_LOW for e in events_b)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_no_events_when_no_previous_snapshot() -> None:
    """First snapshot for a device should never produce transition events."""
    proc = EventProcessor()
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 5
        mock_cfg.THRESHOLD_LOAD_PERCENT = 90
        mock_cfg.THRESHOLD_TEMPERATURE_C = 50
        events = proc.process(_snap(ups_status="OB", battery_percent=5.0))
    # DEVICE_ONLINE is acceptable on first recovery, but no transition events
    assert not any(
        e.event_type
        in (EventType.ON_BATTERY, EventType.BATTERY_LOW, EventType.POWER_RESTORED)
        for e in events
    )


def test_battery_low_no_event_when_battery_pct_missing() -> None:
    """No BATTERY_LOW event when battery_percent is absent from the snapshot."""
    proc = EventProcessor()
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 5
        mock_cfg.THRESHOLD_LOAD_PERCENT = 90
        mock_cfg.THRESHOLD_TEMPERATURE_C = 50
        proc.process(_snap())  # no battery_percent
        events = proc.process(_snap())
    assert not any(e.event_type == EventType.BATTERY_LOW for e in events)


# ---------------------------------------------------------------------------
# THRESHOLD_CROSSED — temperature (lines 238-250)
# ---------------------------------------------------------------------------


def test_threshold_crossed_on_temperature_spike() -> None:
    """THRESHOLD_CROSSED is emitted when temperature crosses the configured limit."""
    proc = EventProcessor()
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 5
        mock_cfg.THRESHOLD_LOAD_PERCENT = 90
        mock_cfg.THRESHOLD_TEMP_CELSIUS = 45.0
        proc.process(_snap(temperature_c=40.0))
        events = proc.process(_snap(temperature_c=50.0))
    temp_events = [
        e
        for e in events
        if e.event_type == EventType.THRESHOLD_CROSSED
        and e.metadata.get("metric") == "temperature_c"
    ]
    assert len(temp_events) == 1
    assert temp_events[0].metadata["threshold"] == pytest.approx(45.0)
    assert temp_events[0].metadata["value"] == pytest.approx(50.0)


def test_threshold_crossed_temperature_not_emitted_when_already_above_limit() -> None:
    """No THRESHOLD_CROSSED for temperature when previous value was already above limit."""
    proc = EventProcessor()
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 5
        mock_cfg.THRESHOLD_LOAD_PERCENT = 90
        mock_cfg.THRESHOLD_TEMP_CELSIUS = 45.0
        proc.process(_snap(temperature_c=50.0))  # already above limit
        events = proc.process(_snap(temperature_c=55.0))
    temp_events = [
        e
        for e in events
        if e.event_type == EventType.THRESHOLD_CROSSED
        and e.metadata.get("metric") == "temperature_c"
    ]
    assert not temp_events


def test_threshold_crossed_temperature_not_emitted_when_temp_is_none() -> None:
    """No THRESHOLD_CROSSED when temperature fields are None."""
    proc = EventProcessor()
    with patch("src.services.event_processor.config") as mock_cfg:
        mock_cfg.SHUTDOWN_BATTERY_FLOOR_PCT = 5
        mock_cfg.THRESHOLD_LOAD_PERCENT = 90
        mock_cfg.THRESHOLD_TEMP_CELSIUS = 45.0
        proc.process(_snap())  # temperature_c is None
        events = proc.process(_snap())
    assert not any(
        e.event_type == EventType.THRESHOLD_CROSSED
        and e.metadata.get("metric") == "temperature_c"
        for e in events
    )
