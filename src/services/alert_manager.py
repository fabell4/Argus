"""AlertManager — tracks consecutive poll failures and fires notifications."""
from __future__ import annotations

import concurrent.futures
import logging
import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.alert_providers import AlertProvider

_LOG = logging.getLogger(__name__)


class AlertManager:
    """Tracks device poll failures and sends alerts when the threshold is reached."""

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: int = 3600,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._providers: list["AlertProvider"] = []
        self._lock = threading.Lock()

        self._consecutive_failures: int = 0
        self._last_error: str = ""
        self._last_failure_time: datetime | None = None
        self._last_alert_time: datetime | None = None

    # ------------------------------------------------------------------
    # Provider management
    # ------------------------------------------------------------------

    def add_provider(self, provider: "AlertProvider") -> None:
        self._providers.append(provider)

    # ------------------------------------------------------------------
    # Result recording
    # ------------------------------------------------------------------

    def record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            self._last_error = ""

    def record_failure(self, error: str, timestamp: datetime) -> None:
        with self._lock:
            self._consecutive_failures += 1
            self._last_error = error
            self._last_failure_time = timestamp
            count = self._consecutive_failures

        _LOG.warning("Consecutive poll failures: %d (threshold=%d)", count, self._failure_threshold)
        if count >= self._failure_threshold:
            self._maybe_send_alert(error, count, timestamp)

    # ------------------------------------------------------------------
    # Alert dispatch
    # ------------------------------------------------------------------

    def _maybe_send_alert(self, error: str, count: int, timestamp: datetime) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            if self._last_alert_time is not None:
                elapsed = (now - self._last_alert_time).total_seconds()
                if elapsed < self._cooldown_seconds:
                    _LOG.debug("Alert suppressed (cooldown %.0f s remaining).", self._cooldown_seconds - elapsed)
                    return
            self._last_alert_time = now

        if not self._providers:
            _LOG.debug("No alert providers configured.")
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self._providers)) as pool:
            futures = {
                pool.submit(p.send_alert, count, error, timestamp): type(p).__name__
                for p in self._providers
            }
            for future, name in futures.items():
                try:
                    future.result(timeout=15)
                    _LOG.info("Alert sent via %s.", name)
                except Exception as exc:  # noqa: BLE001
                    _LOG.error("Alert via %s failed: %s", name, exc)

    def send_test_alert(self) -> None:
        """Send a test notification to all providers."""
        now = datetime.now(timezone.utc)
        for provider in self._providers:
            try:
                provider.send_alert(0, "Test alert from Argus", now)
                _LOG.info("Test alert sent via %s.", type(provider).__name__)
            except Exception as exc:  # noqa: BLE001
                _LOG.error("Test alert via %s failed: %s", type(provider).__name__, exc)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def last_failure_time(self) -> datetime | None:
        return self._last_failure_time
