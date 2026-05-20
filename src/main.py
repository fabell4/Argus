"""Argus scheduler entry point.

Run with:  python -m src.main

Responsibilities:
- Poll configured devices on a schedule (APScheduler IntervalTrigger)
- Dispatch snapshots to all enabled exporters
- Detect state transitions and emit structured events
- Track poll failures and fire alerts when threshold is exceeded
- React to runtime config changes (interval, exporters, manual trigger, pause)
"""
from __future__ import annotations

import logging
import signal
import socket
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src import config, runtime_config, shared_state
from src.models.event import PowerEvent
from src.models.power_snapshot import PowerSnapshot
from src.exporter_registry import EXPORTER_REGISTRY
from src.services.alert_manager import AlertManager
from src.services.alert_provider_factory import register_all_providers
from src.services.device_registry import upsert_device
from src.services.event_processor import EventProcessor
from src.services.health_server import HealthServer
from src.services.nut_poller import NUTPoller
from src.snapshot_dispatcher import DispatchError, SnapshotDispatcher

_LOG = logging.getLogger(__name__)

_dispatcher: SnapshotDispatcher = SnapshotDispatcher()
_alert_manager: AlertManager | None = None
_scheduler: BackgroundScheduler | None = None
_event_processor: EventProcessor = EventProcessor()
_health_server: HealthServer | None = None
_scheduler_status: dict[str, Any] = {"status": "starting"}


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------

def build_dispatcher() -> SnapshotDispatcher:
    """Build a SnapshotDispatcher populated with all currently enabled exporters."""
    dispatcher = SnapshotDispatcher()
    for name in runtime_config.get_enabled_exporters():
        factory = EXPORTER_REGISTRY.get(name)
        if factory is None:
            _LOG.warning("Unknown exporter: %s", name)
            continue
        exporter = factory()
        if exporter is not None:
            dispatcher.add_exporter(exporter)
            _LOG.info("Registered exporter: %s", name)
    return dispatcher


def build_alert_manager() -> AlertManager:
    """Build an AlertManager with all configured alert providers registered."""
    manager = AlertManager(failure_threshold=config.ALERT_FAILURE_THRESHOLD)
    register_all_providers(manager)
    return manager


def build_scheduler(interval_minutes: int) -> BackgroundScheduler:
    """Build a BackgroundScheduler that fires poll_once on the given interval."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        poll_once,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="argus_poll",
        next_run_time=datetime.now(timezone.utc) if config.POLL_ON_STARTUP else None,
    )
    return scheduler


# ---------------------------------------------------------------------------
# Core poll cycle
# ---------------------------------------------------------------------------

def _get_ups_names(discovery_poller: NUTPoller) -> list[str]:
    """Return the list of UPS names to poll, using auto-discovery when enabled."""
    if not config.NUT_AUTO_DISCOVER:
        return [config.NUT_UPS_NAME]
    try:
        ups_names = discovery_poller.list_ups()
        if not ups_names:
            _LOG.warning("NUT auto-discover returned no devices; falling back to NUT_UPS_NAME.")
            return [config.NUT_UPS_NAME]
        return ups_names
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("NUT auto-discover failed (%s); falling back to NUT_UPS_NAME.", exc)
        return [config.NUT_UPS_NAME]


def _poll_single_device(
    ups_name: str,
) -> tuple[PowerSnapshot, list[PowerEvent]] | tuple[None, list[PowerEvent]]:
    """Poll one UPS device and return (snapshot, events), or (None, offline_events) on failure."""
    device_id = f"nut:{ups_name}@{config.NUT_HOST}"
    poller = NUTPoller(
        host=config.NUT_HOST,
        port=config.NUT_PORT,
        username=config.NUT_USERNAME,
        password=config.NUT_PASSWORD,
        ups_name=ups_name,
    )
    try:
        snapshot, metadata = poller.poll_with_metadata()
        upsert_device({
            "id": device_id,
            "name": metadata.get("ups.model") or ups_name,
            "type": "ups",
            "poller": "nut",
            "host": config.NUT_HOST,
            "port": config.NUT_PORT,
            "enabled": True,
            "model": metadata.get("ups.model"),
            "firmware": metadata.get("ups.firmware"),
            "serial": metadata.get("ups.serial"),
            "manufacturer": metadata.get("ups.mfr"),
            "last_seen": snapshot.timestamp.isoformat(),
        })
        events = _event_processor.process(snapshot)
        try:
            _dispatcher.dispatch(snapshot)
        except DispatchError as exc:
            _LOG.exception("One or more exporters failed for %s: %s", ups_name, exc.failures)
        return snapshot, events
    except Exception as exc:  # noqa: BLE001
        _LOG.exception("Poll failed for %s: %s", ups_name, exc)
        offline_events = _event_processor.record_missed_poll(
            device_id, datetime.now(timezone.utc)
        )
        return None, offline_events


def poll_once() -> None:
    """Execute one full poll cycle: collect → dispatch → detect events.

    Supports multi-device via NUT auto-discovery (LIST UPS) when
    ``NUT_AUTO_DISCOVER=true``; falls back to the single ``NUT_UPS_NAME``
    when auto-discovery is disabled or the daemon is unreachable.
    """
    global _scheduler_status  # pylint: disable=global-statement
    runtime_config.mark_running()
    _LOG.info("Starting poll cycle.")

    discovery_poller = NUTPoller(
        host=config.NUT_HOST,
        port=config.NUT_PORT,
        username=config.NUT_USERNAME,
        password=config.NUT_PASSWORD,
    )
    ups_names = _get_ups_names(discovery_poller)
    _LOG.debug("Polling %d UPS device(s): %s", len(ups_names), ups_names)

    all_events: list[PowerEvent] = []
    any_success = False
    last_snapshot: PowerSnapshot | None = None

    for ups_name in ups_names:
        snapshot, events = _poll_single_device(ups_name)
        all_events.extend(events)
        if snapshot is not None:
            any_success = True
            last_snapshot = snapshot

    now = datetime.now(timezone.utc)
    if any_success:
        runtime_config.set_last_poll_at(now)
        if _alert_manager:
            _alert_manager.record_success()
        _scheduler_status = {"status": "ok", "last_poll_at": now.isoformat()}
        if last_snapshot:
            shared_state.set_last_diagnostics(
                {
                    "last_snapshot": last_snapshot.to_dict(),
                    "events": [e.to_dict() for e in all_events],
                }
            )
        _LOG.info("Poll cycle complete. Devices=%d events=%d", len(ups_names), len(all_events))
    else:
        if _alert_manager:
            _alert_manager.record_failure("All device polls failed.", now)
        _scheduler_status = {"status": "error", "last_error": "All device polls failed."}
        _LOG.error("Poll cycle failed for all %d device(s).", len(ups_names))
    runtime_config.mark_done()


# ---------------------------------------------------------------------------
# Runtime config change handlers
# ---------------------------------------------------------------------------

def _poll_once_for_changes() -> None:
    """Called every 30 s by the control loop to react to UI-driven changes."""
    if runtime_config.consume_poll_trigger():
        _LOG.info("Manual poll trigger detected.")
        poll_once()
        return

    paused = runtime_config.get_scheduler_paused()
    if _scheduler:
        if paused and _scheduler.running:
            _scheduler.pause()
            _LOG.info("Scheduler paused via runtime config.")
        elif not paused and _scheduler.state == 2:  # STATE_PAUSED
            _scheduler.resume()
            _LOG.info("Scheduler resumed via runtime config.")


# ---------------------------------------------------------------------------
# Health status
# ---------------------------------------------------------------------------

def _build_health_status() -> dict[str, Any]:
    """Return the current scheduler health status dict for the health endpoint."""
    return {
        **_scheduler_status,
        "scheduler_running": _scheduler.running if _scheduler else False,
        "scheduler_paused": runtime_config.get_scheduler_paused(),
        "next_poll_at": runtime_config.get_next_poll_at(),
        "last_poll_at": runtime_config.get_last_poll_at(),
    }


# ---------------------------------------------------------------------------
# Environment validation
# ---------------------------------------------------------------------------

def _validate_environment() -> None:
    """Warn at startup if configured alert provider URLs appear unreachable.

    Uses a TCP socket connection so no HTTP library or security-audit
    exceptions are required.  Non-fatal — a warning is logged but the
    scheduler continues regardless.
    """
    checks = [
        ("WEBHOOK_URL", config.WEBHOOK_URL),
        ("GOTIFY_URL", config.GOTIFY_URL),
        ("NTFY_URL", config.NTFY_URL),
        ("APPRISE_URL", config.APPRISE_URL),
    ]
    for name, url in checks:
        if not url:
            continue
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not host:
            _LOG.warning("Alert provider %s has an invalid URL: %s", name, url)
            continue
        try:
            with socket.create_connection((host, port), timeout=3):
                _LOG.debug("Alert provider %s (%s:%s) is reachable.", name, host, port)
        except OSError as exc:
            _LOG.warning(
                "Alert provider %s (%s:%s) appears unreachable at startup: %s"
                " — alerts may not be delivered.",
                name,
                host,
                port,
                exc,
            )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Start the Argus scheduler process: configure, start, and run the control loop."""
    global _dispatcher, _alert_manager, _scheduler, _health_server  # pylint: disable=global-statement

    logging.basicConfig(level=getattr(logging, config.LOG_LEVEL, logging.INFO))
    _LOG.info("Argus scheduler starting.")

    try:
        config.validate()
    except ValueError as exc:
        _LOG.critical("Configuration error: %s", exc)
        sys.exit(1)

    _validate_environment()

    _dispatcher = build_dispatcher()
    _alert_manager = build_alert_manager()
    shared_state.set_alert_manager(_alert_manager)

    interval = runtime_config.get_interval_minutes()
    _scheduler = build_scheduler(interval)
    _scheduler.start()
    _LOG.info("Scheduler started with interval=%d minutes.", interval)

    _health_server = HealthServer(port=config.HEALTH_PORT, status_fn=_build_health_status)
    _health_server.start()

    def _shutdown(_signum: int, _frame: Any) -> None:
        """Signal handler for graceful shutdown."""
        _LOG.info("Shutting down Argus scheduler.")
        if _scheduler and _scheduler.running:
            _scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    _LOG.info("Argus scheduler running. Control loop polling every 30 seconds.")
    while True:
        try:
            _poll_once_for_changes()
            next_job = _scheduler.get_job("argus_poll")
            if next_job and next_job.next_run_time:
                runtime_config.set_next_poll_at(next_job.next_run_time)
        except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            _LOG.exception("Control loop error: %s", exc)
        time.sleep(30)


if __name__ == "__main__":
    main()
