"""AlertManager — tracks consecutive poll failures and fires notifications."""

from __future__ import annotations

import concurrent.futures
import logging
import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from src.constants import AlertSeverity, EventType

if TYPE_CHECKING:
    from src.models.event import PowerEvent
    from src.services.alert_providers import AlertProvider

_LOG = logging.getLogger(__name__)

# Default cooldown for recovery alerts (shorter than the main cooldown).
_RECOVERY_COOLDOWN_SECONDS = 300  # 5 minutes

# Severity for each alertable event type.
_EVENT_SEVERITY: dict[str, AlertSeverity] = {
    EventType.ON_BATTERY: AlertSeverity.HIGH,
    EventType.BATTERY_LOW: AlertSeverity.CRITICAL,
    EventType.DEVICE_OFFLINE: AlertSeverity.CRITICAL,
    EventType.SHUTDOWN_INITIATED: AlertSeverity.CRITICAL,
    EventType.THRESHOLD_CROSSED: AlertSeverity.MEDIUM,
    EventType.POWER_RESTORED: AlertSeverity.LOW,
    EventType.DEVICE_ONLINE: AlertSeverity.LOW,
}

# Human-readable message templates for each event type.
_EVENT_MESSAGES: dict[str, str] = {
    EventType.ON_BATTERY: "{device_id} has switched to battery power",
    EventType.BATTERY_LOW: "{device_id} battery is critically low",
    EventType.DEVICE_OFFLINE: "{device_id} is offline",
    EventType.SHUTDOWN_INITIATED: "{device_id} shutdown has been initiated",
    EventType.THRESHOLD_CROSSED: "{device_id} crossed a configured threshold",
    EventType.POWER_RESTORED: "{device_id} power has been restored",
    EventType.DEVICE_ONLINE: "{device_id} is back online",
}

_RECOVERY_EVENT_TYPES = frozenset({EventType.POWER_RESTORED, EventType.DEVICE_ONLINE})
_ALERTABLE_EVENT_TYPES = frozenset(
    {
        EventType.ON_BATTERY,
        EventType.BATTERY_LOW,
        EventType.DEVICE_OFFLINE,
        EventType.SHUTDOWN_INITIATED,
        EventType.THRESHOLD_CROSSED,
    }
)


def _format_event_message(event: "PowerEvent") -> str:
    template = _EVENT_MESSAGES.get(event.event_type, "Power event on {device_id}")
    return template.format(device_id=event.device_id)


class AlertManager:
    """Tracks device poll failures and sends alerts when the threshold is reached.

    Also dispatches alerts for significant power events (ON_BATTERY, BATTERY_LOW,
    DEVICE_OFFLINE) and optional recovery notifications (POWER_RESTORED, DEVICE_ONLINE).
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: int = 3600,
        test_cooldown_seconds: int = 10,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._test_cooldown_seconds = test_cooldown_seconds
        self._providers: list["AlertProvider"] = []
        self._lock = threading.Lock()

        # Poll-failure tracking
        self._consecutive_failures: int = 0
        self._last_error: str = ""
        self._last_failure_time: datetime | None = None
        self._last_alert_time: datetime | None = None

        # Per-(device_id, event_type) last-alert timestamps
        self._event_alert_times: dict[tuple[str, str], datetime] = {}

        # Test alert throttle
        self._last_test_alert_time: datetime | None = None

    # ------------------------------------------------------------------
    # Provider management
    # ------------------------------------------------------------------

    def add_provider(self, provider: "AlertProvider") -> None:
        """Register an alert provider."""
        self._providers.append(provider)

    # ------------------------------------------------------------------
    # Poll-failure tracking
    # ------------------------------------------------------------------

    def record_success(self) -> None:
        """Record a successful poll, resetting the consecutive failure counter."""
        with self._lock:
            self._consecutive_failures = 0
            self._last_error = ""

    def record_failure(self, error: str, timestamp: datetime) -> None:
        """Record a failed poll; fire an alert when the threshold is reached."""
        with self._lock:
            self._consecutive_failures += 1
            self._last_error = error
            self._last_failure_time = timestamp
            count = self._consecutive_failures

        _LOG.warning(
            "Consecutive poll failures: %d (threshold=%d)",
            count,
            self._failure_threshold,
        )
        if count >= self._failure_threshold:
            self._maybe_send_alert(error, count, timestamp)

    # ------------------------------------------------------------------
    # Power-event alerting
    # ------------------------------------------------------------------

    def record_event(self, event: "PowerEvent") -> None:
        """Fire an alert for a significant power event if alerting is enabled for its type."""
        if event.event_type not in _ALERTABLE_EVENT_TYPES:
            return

        if not self._is_event_type_enabled(event.event_type):
            return

        severity = _EVENT_SEVERITY.get(event.event_type, AlertSeverity.MEDIUM)
        message = _format_event_message(event)
        self._maybe_send_event_alert(event, severity, message, self._cooldown_seconds)

    def record_recovery_event(self, event: "PowerEvent") -> None:
        """Send a recovery notification when a device recovers (power restored / device online)."""
        if event.event_type not in _RECOVERY_EVENT_TYPES:
            return

        if not self._is_recovery_notifications_enabled():
            return

        severity = AlertSeverity.LOW
        message = _format_event_message(event)
        cooldown = self._get_recovery_cooldown_seconds()
        self._maybe_send_event_alert(event, severity, message, cooldown)

    def _is_event_type_enabled(self, event_type: str) -> bool:
        """Check runtime config (with env-var fallback) for per-event-type enable flags."""
        from src import config  # noqa: PLC0415
        from src import runtime_config as rc  # noqa: PLC0415

        alert_cfg: dict[str, Any] = rc.load().get("alert_config", {})
        on_batt = alert_cfg.get("alert_on_battery", config.ALERT_ON_BATTERY)
        batt_low = alert_cfg.get("alert_on_battery_low", config.ALERT_ON_BATTERY_LOW)
        offline = alert_cfg.get(
            "alert_on_device_offline", config.ALERT_ON_DEVICE_OFFLINE
        )
        flags: dict[str, bool] = {
            EventType.ON_BATTERY: on_batt,
            EventType.BATTERY_LOW: batt_low,
            EventType.DEVICE_OFFLINE: offline,
            EventType.SHUTDOWN_INITIATED: batt_low,
            EventType.THRESHOLD_CROSSED: True,
        }
        return flags.get(event_type, True)

    def _is_recovery_notifications_enabled(self) -> bool:
        """Return True if recovery notifications are enabled in config."""
        from src import config  # noqa: PLC0415
        from src import runtime_config as rc  # noqa: PLC0415

        alert_cfg: dict[str, Any] = rc.load().get("alert_config", {})
        default = config.ALERT_RECOVERY_NOTIFICATIONS
        return bool(alert_cfg.get("alert_recovery_notifications", default))

    def _get_recovery_cooldown_seconds(self) -> int:
        """Return the configured recovery-notification cooldown, falling back to env/default."""
        from src import config  # noqa: PLC0415
        from src import runtime_config as rc  # noqa: PLC0415

        alert_cfg: dict[str, Any] = rc.load().get("alert_config", {})
        default = config.ALERT_RECOVERY_COOLDOWN_SECONDS
        raw = alert_cfg.get("recovery_cooldown_seconds", default)
        return int(raw) if isinstance(raw, (int, float)) else default

    def _maybe_send_event_alert(
        self,
        event: "PowerEvent",
        severity: AlertSeverity,
        message: str,
        cooldown: int,
    ) -> None:
        now = datetime.now(timezone.utc)
        key = (event.device_id, event.event_type)

        with self._lock:
            last = self._event_alert_times.get(key)
            if last is not None:
                elapsed = (now - last).total_seconds()
                if elapsed < cooldown:
                    _LOG.debug(
                        "Event alert suppressed for %s/%s (cooldown %.0f s remaining).",
                        event.device_id,
                        event.event_type,
                        cooldown - elapsed,
                    )
                    return
            self._event_alert_times[key] = now

        if not self._providers:
            _LOG.debug("No alert providers configured.")
            return

        eligible = [p for p in self._providers if p.meets_min_severity(str(severity))]
        if not eligible:
            _LOG.debug(
                "No providers eligible for severity %s (all below their min_severity).",
                severity,
            )
            return

        _LOG.info(
            "Dispatching %s alert for %s/%s: %s",
            severity,
            event.device_id,
            event.event_type,
            message,
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(eligible)) as pool:
            futures = {
                pool.submit(
                    p.send_event_alert,
                    event.event_type,
                    event.device_id,
                    message,
                    str(severity),
                    event.timestamp,
                ): type(p).__name__
                for p in eligible
            }
            for future, name in futures.items():
                try:
                    future.result(timeout=15)
                    _LOG.info("Event alert sent via %s.", name)
                except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                    _LOG.exception("Event alert via %s failed: %s", name, exc)

    # ------------------------------------------------------------------
    # Poll-failure alert dispatch
    # ------------------------------------------------------------------

    def _maybe_send_alert(self, error: str, count: int, timestamp: datetime) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            if self._last_alert_time is not None:
                elapsed = (now - self._last_alert_time).total_seconds()
                if elapsed < self._cooldown_seconds:
                    remaining = self._cooldown_seconds - elapsed
                    _LOG.debug(
                        "Alert suppressed (cooldown %.0f s remaining).", remaining
                    )
                    return
            self._last_alert_time = now

        if not self._providers:
            _LOG.debug("No alert providers configured.")
            return

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(self._providers)
        ) as pool:
            futures = {
                pool.submit(p.send_alert, count, error, timestamp): type(p).__name__
                for p in self._providers
            }
            for future, name in futures.items():
                try:
                    future.result(timeout=15)
                    _LOG.info("Alert sent via %s.", name)
                except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                    _LOG.exception("Alert via %s failed: %s", name, exc)

    def send_test_alert(self) -> None:
        """Send a test notification to all providers, subject to a minimum cooldown."""
        now = datetime.now(timezone.utc)
        with self._lock:
            if self._last_test_alert_time is not None:
                elapsed = (now - self._last_test_alert_time).total_seconds()
                if elapsed < self._test_cooldown_seconds:
                    remaining = self._test_cooldown_seconds - elapsed
                    _LOG.warning(
                        "Test alert suppressed; cooldown active (%.0f s remaining).",
                        remaining,
                    )
                    raise RuntimeError(
                        f"Test alert cooldown active. Try again in {remaining:.0f} seconds."
                    )
            self._last_test_alert_time = now

        for provider in self._providers:
            try:
                provider.send_alert(0, "Test alert from Argus", now)
                _LOG.info("Test alert sent via %s.", type(provider).__name__)
            except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                _LOG.exception(
                    "Test alert via %s failed: %s", type(provider).__name__, exc
                )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def consecutive_failures(self) -> int:
        """Number of consecutive poll failures since the last success."""
        return self._consecutive_failures

    @property
    def last_error(self) -> str:
        """Error message from the most recent failed poll."""
        return self._last_error

    @property
    def last_failure_time(self) -> datetime | None:
        """Timestamp of the most recent failed poll."""
        return self._last_failure_time
