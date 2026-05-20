"""EventProcessor — detects device state transitions between consecutive snapshots."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src import config
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
        # device_id → consecutive missed-poll count
        self._missed_counts: dict[str, int] = {}
        # devices currently considered offline
        self._offline_devices: set[str] = set()
        # devices for which SHUTDOWN_INITIATED has been fired (reset on power-restored)
        self._shutdown_fired: set[str] = set()

    def process(self, snapshot: PowerSnapshot) -> list[PowerEvent]:
        """Evaluate a new snapshot against the previous one; return any events."""
        events: list[PowerEvent] = []
        device_id = snapshot.device_id

        # Device came back after being offline
        if device_id in self._offline_devices:
            self._offline_devices.discard(device_id)
            events.append(
                PowerEvent(
                    timestamp=datetime.now(timezone.utc),
                    device_id=device_id,
                    event_type=EventType.DEVICE_ONLINE,
                    metadata={"missed_polls": self._missed_counts.get(device_id, 0)},
                )
            )
            _LOG.info("Device %s is back online.", device_id)

        # Reset missed-poll counter on successful snapshot
        self._missed_counts[device_id] = 0

        prev = self._previous.get(device_id)
        if prev is not None:
            events.extend(self._detect_ups_status_change(prev, snapshot))
            events.extend(self._detect_battery_low(prev, snapshot))
            events.extend(self._detect_shutdown_initiated(snapshot))
            events.extend(self._detect_threshold_crossed(prev, snapshot))

        self._previous[device_id] = snapshot
        return events

    def record_missed_poll(
        self, device_id: str, timestamp: datetime | None = None
    ) -> list[PowerEvent]:
        """Called by the scheduler when a device poll fails.

        Returns DEVICE_OFFLINE event when the missed-poll threshold is reached.
        """
        count = self._missed_counts.get(device_id, 0) + 1
        self._missed_counts[device_id] = count
        threshold = config.DEVICE_OFFLINE_MISSED_POLLS

        events: list[PowerEvent] = []
        if count >= threshold and device_id not in self._offline_devices:
            self._offline_devices.add(device_id)
            ts = timestamp or datetime.now(timezone.utc)
            events.append(
                PowerEvent(
                    timestamp=ts,
                    device_id=device_id,
                    event_type=EventType.DEVICE_OFFLINE,
                    metadata={"missed_polls": count, "threshold": threshold},
                )
            )
            _LOG.warning(
                "Device %s marked offline after %d missed polls.", device_id, count
            )
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
            # Power restored — clear any pending shutdown flag
            self._shutdown_fired.discard(curr.device_id)
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

    def _detect_shutdown_initiated(self, curr: PowerSnapshot) -> list[PowerEvent]:
        """Fire SHUTDOWN_INITIATED when battery drops below the critical floor while on battery."""
        events: list[PowerEvent] = []
        if curr.device_id in self._shutdown_fired:
            return events

        curr_status = curr.ups_status or ""
        on_battery = UPSStatus.ON_BATTERY in curr_status
        if not on_battery:
            return events

        floor = config.SHUTDOWN_BATTERY_FLOOR_PCT
        if curr.battery_percent is not None and curr.battery_percent <= floor:
            self._shutdown_fired.add(curr.device_id)
            events.append(
                PowerEvent(
                    timestamp=datetime.now(timezone.utc),
                    device_id=curr.device_id,
                    event_type=EventType.SHUTDOWN_INITIATED,
                    metadata={
                        "battery_percent": curr.battery_percent,
                        "floor_percent": floor,
                    },
                )
            )
            _LOG.critical(
                "Device %s battery critical (%.1f%% ≤ %.1f%%); shutdown imminent.",
                curr.device_id,
                curr.battery_percent,
                floor,
            )
        return events

    def _detect_threshold_crossed(
        self, prev: PowerSnapshot, curr: PowerSnapshot
    ) -> list[PowerEvent]:
        """Fire THRESHOLD_CROSSED when load or temperature crosses configured limits."""
        events: list[PowerEvent] = []
        now = datetime.now(timezone.utc)

        load_limit = config.THRESHOLD_LOAD_PERCENT
        if (
            curr.load_percent is not None
            and prev.load_percent is not None
            and curr.load_percent >= load_limit
            and prev.load_percent < load_limit
        ):
            events.append(
                PowerEvent(
                    timestamp=now,
                    device_id=curr.device_id,
                    event_type=EventType.THRESHOLD_CROSSED,
                    metadata={
                        "metric": "load_percent",
                        "value": curr.load_percent,
                        "threshold": load_limit,
                    },
                )
            )
            _LOG.warning(
                "Device %s load crossed %.1f%% (now %.1f%%).",
                curr.device_id,
                load_limit,
                curr.load_percent,
            )

        temp_limit = config.THRESHOLD_TEMP_CELSIUS
        if (
            curr.temperature_c is not None
            and prev.temperature_c is not None
            and curr.temperature_c >= temp_limit
            and prev.temperature_c < temp_limit
        ):
            events.append(
                PowerEvent(
                    timestamp=now,
                    device_id=curr.device_id,
                    event_type=EventType.THRESHOLD_CROSSED,
                    metadata={
                        "metric": "temperature_c",
                        "value": curr.temperature_c,
                        "threshold": temp_limit,
                    },
                )
            )
            _LOG.warning(
                "Device %s temperature crossed %.1f°C (now %.1f°C).",
                curr.device_id,
                temp_limit,
                curr.temperature_c,
            )

        return events
