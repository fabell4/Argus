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
import sys
import time
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src import config, runtime_config, shared_state
from src.exporter_registry import EXPORTER_REGISTRY
from src.services.alert_manager import AlertManager
from src.services.alert_provider_factory import register_all_providers
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
    manager = AlertManager(failure_threshold=config.ALERT_FAILURE_THRESHOLD)
    register_all_providers(manager)
    return manager


def build_scheduler(interval_minutes: int) -> BackgroundScheduler:
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

def poll_once() -> None:
    """Execute one full poll cycle: collect → dispatch → detect events."""
    global _scheduler_status
    runtime_config.mark_running()
    _LOG.info("Starting poll cycle.")
    try:
        poller = NUTPoller(
            host=config.NUT_HOST,
            port=config.NUT_PORT,
            username=config.NUT_USERNAME,
            password=config.NUT_PASSWORD,
            ups_name=config.NUT_UPS_NAME,
        )
        snapshot = poller.poll()
        events = _event_processor.process(snapshot)

        try:
            _dispatcher.dispatch(snapshot)
        except DispatchError as exc:
            _LOG.error("One or more exporters failed: %s", exc.failures)

        now = datetime.now(timezone.utc)
        runtime_config.set_last_poll_at(now)
        if _alert_manager:
            _alert_manager.record_success()

        _scheduler_status = {"status": "ok", "last_poll_at": now.isoformat()}
        shared_state.set_last_diagnostics(
            {"last_snapshot": snapshot.to_dict(), "events": [e.to_dict() for e in events]}
        )
        _LOG.info("Poll cycle complete. Events detected: %d", len(events))
    except Exception as exc:  # noqa: BLE001
        _LOG.error("Poll cycle failed: %s", exc)
        if _alert_manager:
            _alert_manager.record_failure(str(exc), datetime.now(timezone.utc))
        _scheduler_status = {"status": "error", "last_error": str(exc)}
    finally:
        runtime_config.mark_done()


# ---------------------------------------------------------------------------
# Runtime config change handlers
# ---------------------------------------------------------------------------

def _poll_once_for_changes() -> None:
    """Called every 30 s by the control loop to react to UI-driven changes."""
    global _dispatcher, _scheduler

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
    return {
        **_scheduler_status,
        "scheduler_running": _scheduler.running if _scheduler else False,
        "scheduler_paused": runtime_config.get_scheduler_paused(),
        "next_poll_at": runtime_config.get_next_poll_at(),
        "last_poll_at": runtime_config.get_last_poll_at(),
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    global _dispatcher, _alert_manager, _scheduler, _health_server

    logging.basicConfig(level=getattr(logging, config.LOG_LEVEL, logging.INFO))
    _LOG.info("Argus scheduler starting.")

    try:
        config.validate()
    except ValueError as exc:
        _LOG.critical("Configuration error: %s", exc)
        sys.exit(1)

    _dispatcher = build_dispatcher()
    _alert_manager = build_alert_manager()
    shared_state.set_alert_manager(_alert_manager)

    interval = runtime_config.get_interval_minutes()
    _scheduler = build_scheduler(interval)
    _scheduler.start()
    _LOG.info("Scheduler started with interval=%d minutes.", interval)

    _health_server = HealthServer(port=config.HEALTH_PORT, status_fn=_build_health_status)
    _health_server.start()

    def _shutdown(signum: int, frame: Any) -> None:
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
        except Exception as exc:  # noqa: BLE001
            _LOG.error("Control loop error: %s", exc)
        time.sleep(30)


if __name__ == "__main__":
    main()
