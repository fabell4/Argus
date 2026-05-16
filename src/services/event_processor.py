"""EventProcessor — detects device state transitions between consecutive snapshots."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.constants import EventType, UPSStatus
from src.models.event import PowerEvent
from src.models.power_snapshot import PowerSnapshot

_LOG = logging.getLogger(__name__)

_BATTERY_LOW_THRESHOLD = 20.0  # percent


class EventProcessor:
    """Compares consecutive snapshots per device and emits structured events."""

    def __init__(self) -> None:
        # device_id → last PowerSnapshot
        self._previous: dict[str, PowerSnapshot] = {}

    def process(self, snapshot: PowerSnapshot) -> list[PowerEvent]:
        """Evaluate a new snapshot against the previous one; return any events."""
        events: list[PowerEvent] = []
        prev = self._previous.get(snapshot.device_id)

        if prev is not None:
            events.extend(self._detect_ups_status_change(prev, snapshot))
            events.extend(self._detect_battery_low(prev, snapshot))

        self._previous[snapshot.device_id] = snapshot
        return events

    # ------------------------------------------------------------------
    # Transition detectors
    # ------------------------------------------------------------------

    def _detect_ups_status_change(
        self, prev: PowerSnapshot, curr: PowerSnapshot
    ) -> list[PowerEvent]:
        events: list[PowerEvent] = []
        prev_status = prev.ups_status or ""
        curr_status = curr.ups_status or ""

        if prev_status == curr_status:
            return events

        now = datetime.now(timezone.utc)

        on_battery_now = UPSStatus.ON_BATTERY in curr_status
        on_battery_before = UPSStatus.ON_BATTERY in prev_status

        if on_battery_now and not on_battery_before:
            events.append(
                PowerEvent(
                    timestamp=now,
                    device_id=curr.device_id,
                    event_type=EventType.ON_BATTERY,
                    metadata={"previous_status": prev_status, "current_status": curr_status},
                )
            )
            _LOG.warning("Device %s switched to battery power.", curr.device_id)

        elif not on_battery_now and on_battery_before:
            events.append(
                PowerEvent(
                    timestamp=now,
                    device_id=curr.device_id,
                    event_type=EventType.POWER_RESTORED,
                    metadata={"previous_status": prev_status, "current_status": curr_status},
                )
            )
            _LOG.info("Device %s restored to mains power.", curr.device_id)

        return events

    def _detect_battery_low(
        self, prev: PowerSnapshot, curr: PowerSnapshot
    ) -> list[PowerEvent]:
        events: list[PowerEvent] = []
        prev_pct = prev.battery_percent
        curr_pct = curr.battery_percent

        if curr_pct is None or prev_pct is None:
            return events

        was_low = prev_pct <= _BATTERY_LOW_THRESHOLD
        is_low = curr_pct <= _BATTERY_LOW_THRESHOLD

        if is_low and not was_low:
            events.append(
                PowerEvent(
                    timestamp=datetime.now(timezone.utc),
                    device_id=curr.device_id,
                    event_type=EventType.BATTERY_LOW,
                    metadata={
                        "battery_percent": curr_pct,
                        "threshold": _BATTERY_LOW_THRESHOLD,
                    },
                )
            )
            _LOG.warning(
                "Device %s battery low: %.1f%%.", curr.device_id, curr_pct
            )

        return events
