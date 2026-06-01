"""Tests for src.main builder functions, _build_health_status, _get_ups_names, etc."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ===========================================================================
# types module — trivial import coverage
# ===========================================================================


def test_types_module_importable() -> None:
    """Verify that JsonDict is importable and usable from src.types."""
    from src.types import JsonDict

    d: JsonDict = {"key": "value"}
    assert d["key"] == "value"


# ===========================================================================
# build_dispatcher
# ===========================================================================


def test_build_dispatcher_adds_enabled_exporters() -> None:
    """Enabled exporters from runtime config are added to the dispatcher."""
    from src import main as main_mod

    mock_exporter = MagicMock()
    mock_factory = MagicMock(return_value=mock_exporter)

    with patch(
        "src.main.runtime_config.get_enabled_exporters", return_value=["sqlite"]
    ):
        with patch("src.main.EXPORTER_REGISTRY", {"sqlite": mock_factory}):
            dispatcher = main_mod.build_dispatcher()

    assert mock_exporter in dispatcher._exporters  # noqa: SLF001


def test_build_dispatcher_skips_unknown_exporter() -> None:
    """Unknown exporter names are silently skipped by build_dispatcher."""
    from src import main as main_mod

    with patch(
        "src.main.runtime_config.get_enabled_exporters", return_value=["nonexistent"]
    ):
        with patch("src.main.EXPORTER_REGISTRY", {}):
            dispatcher = main_mod.build_dispatcher()

    assert len(dispatcher._exporters) == 0  # noqa: SLF001


def test_build_dispatcher_skips_none_factory_result() -> None:
    """A factory returning None does not add an exporter to the dispatcher."""
    from src import main as main_mod

    mock_factory = MagicMock(return_value=None)
    with patch("src.main.runtime_config.get_enabled_exporters", return_value=["csv"]):
        with patch("src.main.EXPORTER_REGISTRY", {"csv": mock_factory}):
            dispatcher = main_mod.build_dispatcher()

    assert len(dispatcher._exporters) == 0  # noqa: SLF001


# ===========================================================================
# build_alert_manager
# ===========================================================================


def test_build_alert_manager_returns_alert_manager() -> None:
    """build_alert_manager returns an AlertManager instance."""
    from src import main as main_mod
    from src.services.alert_manager import AlertManager

    with patch("src.main.register_all_providers"):
        manager = main_mod.build_alert_manager()

    assert isinstance(manager, AlertManager)


def test_build_alert_manager_calls_register_all_providers() -> None:
    """build_alert_manager calls register_all_providers exactly once."""
    from src import main as main_mod

    with patch("src.main.register_all_providers") as mock_register:
        main_mod.build_alert_manager()

    mock_register.assert_called_once()


# ===========================================================================
# build_scheduler
# ===========================================================================


def test_build_scheduler_creates_background_scheduler() -> None:
    """build_scheduler returns a BackgroundScheduler instance."""
    from src import main as main_mod
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = main_mod.build_scheduler(5)
    assert isinstance(scheduler, BackgroundScheduler)


def test_build_scheduler_adds_argus_poll_job() -> None:
    """build_scheduler registers the argus_poll job."""
    from src import main as main_mod

    scheduler = main_mod.build_scheduler(5)
    job = scheduler.get_job("argus_poll")
    assert job is not None


# ===========================================================================
# _get_ups_names
# ===========================================================================


def test_get_ups_names_returns_config_name_when_auto_discover_false() -> None:
    """_get_ups_names returns the configured name when auto-discover is disabled."""
    from src import main as main_mod

    mock_poller = MagicMock()

    with patch(
        "src.main.runtime_config.get_nut_config",
        return_value={
            "auto_discover": False,
            "ups_name": "ups1",
            "ups_names": ["ups1"],
            "host": "localhost",
            "port": 3493,
            "username": "",
            "password": "",
        },
    ):
        result = main_mod._get_ups_names(mock_poller)  # noqa: SLF001

    assert result == ["ups1"]


def test_get_ups_names_returns_multiple_config_names_when_auto_discover_false() -> None:
    """_get_ups_names returns all configured names when auto-discover is disabled."""
    from src import main as main_mod

    mock_poller = MagicMock()

    with patch(
        "src.main.runtime_config.get_nut_config",
        return_value={
            "auto_discover": False,
            "ups_name": "ups1,ups2",
            "ups_names": ["ups1", "ups2"],
            "host": "localhost",
            "port": 3493,
            "username": "",
            "password": "",
        },
    ):
        result = main_mod._get_ups_names(mock_poller)  # noqa: SLF001

    assert result == ["ups1", "ups2"]


def test_get_ups_names_uses_list_ups_when_auto_discover_true() -> None:
    """_get_ups_names calls list_ups when auto-discover is enabled."""
    from src import main as main_mod

    mock_poller = MagicMock()
    mock_poller.list_ups.return_value = ["ups1", "ups2"]

    with patch(
        "src.main.runtime_config.get_nut_config",
        return_value={
            "auto_discover": True,
            "ups_name": "ups",
            "ups_names": ["ups"],
            "host": "localhost",
            "port": 3493,
            "username": "",
            "password": "",
        },
    ):
        result = main_mod._get_ups_names(mock_poller)  # noqa: SLF001

    assert result == ["ups1", "ups2"]


def test_get_ups_names_falls_back_on_empty_list() -> None:
    """_get_ups_names falls back to the configured name when list_ups returns empty."""
    from src import main as main_mod

    mock_poller = MagicMock()
    mock_poller.list_ups.return_value = []

    with patch(
        "src.main.runtime_config.get_nut_config",
        return_value={
            "auto_discover": True,
            "ups_name": "fallback_ups_1,fallback_ups_2",
            "ups_names": ["fallback_ups_1", "fallback_ups_2"],
            "host": "localhost",
            "port": 3493,
            "username": "",
            "password": "",
        },
    ):
        result = main_mod._get_ups_names(mock_poller)  # noqa: SLF001

    assert result == ["fallback_ups_1", "fallback_ups_2"]


def test_get_ups_names_falls_back_on_exception() -> None:
    """_get_ups_names falls back to the configured name when list_ups raises."""
    from src import main as main_mod

    mock_poller = MagicMock()
    mock_poller.list_ups.side_effect = OSError("Connection refused")

    with patch(
        "src.main.runtime_config.get_nut_config",
        return_value={
            "auto_discover": True,
            "ups_name": "fallback_ups_1,fallback_ups_2",
            "ups_names": ["fallback_ups_1", "fallback_ups_2"],
            "host": "localhost",
            "port": 3493,
            "username": "",
            "password": "",
        },
    ):
        result = main_mod._get_ups_names(mock_poller)  # noqa: SLF001

    assert result == ["fallback_ups_1", "fallback_ups_2"]


# ===========================================================================
# _build_health_status
# ===========================================================================


def test_build_health_status_contains_expected_keys() -> None:
    """_build_health_status response contains status, scheduler_running, and scheduler_paused."""
    import src.main as main_mod

    main_mod._scheduler_status = {"status": "ok"}
    main_mod._scheduler = None  # no scheduler

    with patch("src.main.runtime_config.get_scheduler_paused", return_value=False):
        with patch("src.main.runtime_config.get_next_poll_at", return_value=None):
            with patch("src.main.runtime_config.get_last_poll_at", return_value=None):
                result = main_mod._build_health_status()

    assert "status" in result
    assert "scheduler_running" in result
    assert "scheduler_paused" in result


def test_build_health_status_reflects_scheduler_running() -> None:
    """scheduler_running is True when the scheduler reports running=True."""
    import src.main as main_mod

    mock_scheduler = MagicMock()
    mock_scheduler.running = True
    main_mod._scheduler = mock_scheduler
    main_mod._scheduler_status = {"status": "ok"}

    with patch("src.main.runtime_config.get_scheduler_paused", return_value=False):
        with patch("src.main.runtime_config.get_next_poll_at", return_value=None):
            with patch("src.main.runtime_config.get_last_poll_at", return_value=None):
                result = main_mod._build_health_status()

    assert result["scheduler_running"] is True
    main_mod._scheduler = None  # cleanup


# ===========================================================================
# _validate_environment
# ===========================================================================


def test_validate_environment_skips_empty_urls() -> None:
    """_validate_environment skips socket checks when all provider URLs are empty."""
    import src.main as main_mod

    # Should not call socket.create_connection when all URLs are empty
    with patch("src.main.config.WEBHOOK_URL", ""):
        with patch("src.main.config.GOTIFY_URL", ""):
            with patch("src.main.config.NTFY_URL", ""):
                with patch("src.main.config.APPRISE_URL", ""):
                    with patch("socket.create_connection") as mock_conn:
                        main_mod._validate_environment()
                        mock_conn.assert_not_called()


def test_validate_environment_warns_on_unreachable_url() -> None:
    """_validate_environment logs a warning but does not raise on unreachable URL."""
    import src.main as main_mod

    with patch("src.main.config.WEBHOOK_URL", "https://unreachable.example.com"):
        with patch("src.main.config.GOTIFY_URL", ""):
            with patch("src.main.config.NTFY_URL", ""):
                with patch("src.main.config.APPRISE_URL", ""):
                    with patch(
                        "socket.create_connection", side_effect=OSError("refused")
                    ):
                        # Should not raise — just warn
                        main_mod._validate_environment()


# ===========================================================================
# exporter_registry factory functions
# ===========================================================================


def test_exporter_registry_csv_factory() -> None:
    """The csv factory in EXPORTER_REGISTRY returns a non-None exporter."""
    from src.constants import ExporterType
    from src.exporter_registry import EXPORTER_REGISTRY

    factory = EXPORTER_REGISTRY.get(ExporterType.CSV)
    assert factory is not None
    result = factory()
    assert result is not None


def test_exporter_registry_energy_factory() -> None:
    """The energy factory in EXPORTER_REGISTRY returns a non-None exporter."""
    from src.constants import ExporterType
    from src.exporter_registry import EXPORTER_REGISTRY

    with patch(
        "src.exporters.energy_accumulator.EnergyAccumulatorExporter._init_prometheus"
    ):
        factory = EXPORTER_REGISTRY.get(ExporterType.ENERGY)
        assert factory is not None
        result = factory()
    assert result is not None


def test_exporter_registry_loki_factory_when_url_set() -> None:
    """The loki factory is present in EXPORTER_REGISTRY when a URL is configured."""
    from src.constants import ExporterType
    from src.exporter_registry import EXPORTER_REGISTRY

    with patch("src.config.LOKI_URL", "https://loki.example.com"):
        factory = EXPORTER_REGISTRY.get(ExporterType.LOKI)
        assert factory is not None


def test_exporter_registry_influxdb_factory_when_url_set() -> None:
    """The influxdb factory is present in EXPORTER_REGISTRY when credentials are configured."""
    from src.constants import ExporterType
    from src.exporter_registry import EXPORTER_REGISTRY

    with patch("src.config.INFLUXDB_URL", "https://influxdb:8086"):
        with patch("src.config.INFLUXDB_TOKEN", "tok"):
            with patch("src.config.INFLUXDB_ORG", "org"):
                with patch("src.config.INFLUXDB_BUCKET", "bkt"):
                    factory = EXPORTER_REGISTRY.get(ExporterType.INFLUXDB)
                    assert factory is not None


# ===========================================================================
# _poll_once_for_changes
# ===========================================================================


def test_poll_once_for_changes_calls_poll_once_on_trigger() -> None:
    """_poll_once_for_changes calls poll_once when a trigger is pending."""
    import src.main as main_mod

    with patch("src.main.runtime_config.consume_poll_trigger", return_value=True):
        with patch("src.main.poll_once") as mock_poll:
            main_mod._poll_once_for_changes()
            mock_poll.assert_called_once()


def test_poll_once_for_changes_pauses_scheduler() -> None:
    """_poll_once_for_changes pauses a running scheduler when the paused flag is set."""
    import src.main as main_mod

    mock_scheduler = MagicMock()
    mock_scheduler.running = True
    mock_scheduler.state = 1  # STATE_RUNNING
    main_mod._scheduler = mock_scheduler

    with patch("src.main.runtime_config.consume_poll_trigger", return_value=False):
        with patch("src.main.runtime_config.get_scheduler_paused", return_value=True):
            main_mod._poll_once_for_changes()

    mock_scheduler.pause.assert_called_once()
    main_mod._scheduler = None


def test_poll_once_for_changes_resumes_scheduler() -> None:
    """_poll_once_for_changes resumes a paused scheduler when the paused flag is cleared."""
    import src.main as main_mod

    mock_scheduler = MagicMock()
    mock_scheduler.running = True
    mock_scheduler.state = 2  # STATE_PAUSED
    main_mod._scheduler = mock_scheduler

    with patch("src.main.runtime_config.consume_poll_trigger", return_value=False):
        with patch("src.main.runtime_config.get_scheduler_paused", return_value=False):
            main_mod._poll_once_for_changes()

    mock_scheduler.resume.assert_called_once()
    main_mod._scheduler = None


# ===========================================================================
# poll_once (simplified integration)
# ===========================================================================


def test_poll_once_records_success_on_good_snapshot() -> None:
    """poll_once calls record_success on the alert manager after a successful poll."""
    import src.main as main_mod
    from datetime import datetime, timezone
    from src.models.power_snapshot import PowerSnapshot

    snap = PowerSnapshot(
        timestamp=datetime.now(timezone.utc),
        device_id="nut:ups@localhost",
        device_type="ups",
        power_watts=100.0,
    )
    mock_manager = MagicMock()

    with patch("src.main._get_ups_names", return_value=["ups"]):
        with patch("src.main._poll_single_device", return_value=(snap, [])):
            with patch("src.main.runtime_config.mark_running"):
                with patch("src.main.runtime_config.mark_done"):
                    with patch("src.main.runtime_config.set_last_poll_at"):
                        main_mod._alert_manager = mock_manager
                        main_mod.poll_once()

    mock_manager.record_success.assert_called_once()
    main_mod._alert_manager = None


def test_poll_once_records_failure_when_no_snapshots() -> None:
    """poll_once calls record_failure on the alert manager when no snapshot is returned."""
    import src.main as main_mod

    mock_manager = MagicMock()

    with patch("src.main._get_ups_names", return_value=["ups"]):
        with patch("src.main._poll_single_device", return_value=(None, [])):
            with patch("src.main.runtime_config.mark_running"):
                with patch("src.main.runtime_config.mark_done"):
                    main_mod._alert_manager = mock_manager
                    main_mod.poll_once()

    mock_manager.record_failure.assert_called_once()
    main_mod._alert_manager = None


# ===========================================================================
# _poll_single_device (lines 112-147)
# ===========================================================================


def test_poll_single_device_success_path() -> None:
    """_poll_single_device returns a snapshot on a successful NUT poll."""
    import src.main as main_mod
    from datetime import datetime, timezone
    from src.models.power_snapshot import PowerSnapshot

    snap = PowerSnapshot(
        timestamp=datetime.now(timezone.utc),
        device_id="nut:ups@localhost",
        device_type="ups",
        power_watts=100.0,
    )
    mock_poller = MagicMock()
    mock_poller.poll_with_metadata.return_value = (snap, {"ups.model": "APC"})

    with (
        patch("src.main.NUTPoller", return_value=mock_poller),
        patch("src.main.upsert_device"),
        patch("src.main._event_processor") as mock_ep,
        patch("src.main._dispatcher"),
    ):
        mock_ep.process.return_value = []
        result_snap, result_events = main_mod._poll_single_device("ups")  # noqa: SLF001

    assert result_snap is snap
    assert not result_events


def test_poll_single_device_failure_path_returns_none() -> None:
    """_poll_single_device returns (None, offline_events) when the poll raises OSError."""
    import src.main as main_mod

    mock_poller = MagicMock()
    mock_poller.poll_with_metadata.side_effect = OSError("connection refused")

    with (
        patch("src.main.NUTPoller", return_value=mock_poller),
        patch("src.main._event_processor") as mock_ep,
    ):
        from datetime import datetime, timezone
        from src.models.event import PowerEvent
        from src.constants import EventType

        offline_event = PowerEvent(
            timestamp=datetime.now(timezone.utc),
            device_id="nut:ups@localhost",
            event_type=EventType.DEVICE_OFFLINE,
            metadata={},
        )
        mock_ep.record_missed_poll.return_value = [offline_event]
        result_snap, result_events = main_mod._poll_single_device("ups")  # noqa: SLF001

    assert result_snap is None
    assert len(result_events) == 1


def test_poll_single_device_dispatch_error_logged() -> None:
    """_poll_single_device logs a dispatch error but still returns the snapshot."""
    import src.main as main_mod
    from datetime import datetime, timezone
    from src.models.power_snapshot import PowerSnapshot
    from src.snapshot_dispatcher import DispatchError

    snap = PowerSnapshot(
        timestamp=datetime.now(timezone.utc),
        device_id="nut:ups@localhost",
        device_type="ups",
    )
    mock_poller = MagicMock()
    mock_poller.poll_with_metadata.return_value = (snap, {})

    with (
        patch("src.main.NUTPoller", return_value=mock_poller),
        patch("src.main.upsert_device"),
        patch("src.main._event_processor") as mock_ep,
        patch("src.main._dispatcher") as mock_disp,
    ):
        mock_ep.process.return_value = []
        mock_disp.dispatch.side_effect = DispatchError({"SQLiteExporter": "disk full"})
        result_snap, _ = main_mod._poll_single_device("ups")  # noqa: SLF001

    assert result_snap is snap


# ===========================================================================
# _record_events_with_alert_manager (lines 153, 156-159)
# ===========================================================================


def test_record_events_with_alert_manager_no_manager_returns_early() -> None:
    """When _alert_manager is None, _record_events_with_alert_manager is a no-op."""
    import src.main as main_mod

    main_mod._alert_manager = None  # noqa: SLF001
    # Should not raise
    main_mod._record_events_with_alert_manager([])  # noqa: SLF001


def test_record_events_with_alert_manager_dispatches_recovery_events() -> None:
    """Recovery event types are forwarded to record_recovery_event."""
    import src.main as main_mod
    from datetime import datetime, timezone
    from src.models.event import PowerEvent
    from src.constants import EventType

    mock_mgr = MagicMock()
    main_mod._alert_manager = mock_mgr  # noqa: SLF001

    recovery = PowerEvent(
        timestamp=datetime.now(timezone.utc),
        device_id="nut:ups@localhost",
        event_type=EventType.POWER_RESTORED,
        metadata={},
    )
    regular = PowerEvent(
        timestamp=datetime.now(timezone.utc),
        device_id="nut:ups@localhost",
        event_type=EventType.ON_BATTERY,
        metadata={},
    )
    main_mod._record_events_with_alert_manager([recovery, regular])  # noqa: SLF001

    mock_mgr.record_success.assert_called_once()
    mock_mgr.record_recovery_event.assert_called_once_with(recovery)
    mock_mgr.record_event.assert_called_once_with(regular)
    main_mod._alert_manager = None  # noqa: SLF001
    main_mod._alert_manager = None


# ===========================================================================
# Scheduler persistence — poll interval restored from runtime_config.json
# ===========================================================================


def test_scheduler_restores_poll_interval_from_runtime_config(
    tmp_path: "pathlib.Path",
) -> None:
    """Simulates a scheduler restart: a saved poll interval is read from
    runtime_config.json and used to configure the APScheduler job interval.

    This exercises the startup sequence::

        interval = runtime_config.get_interval_minutes()
        _scheduler = build_scheduler(interval)
    """
    import json
    import pathlib
    import src.main as main_mod
    from src import runtime_config as rc_mod

    # Write a runtime_config.json with a non-default interval.
    config_file = tmp_path / "runtime_config.json"
    config_file.write_text(json.dumps({"poll_interval_minutes": 7}), encoding="utf-8")

    # Patch the module-level path used by runtime_config so it reads our test file.
    with patch.object(rc_mod, "_CONFIG_PATH", str(config_file)):
        restored_interval = rc_mod.get_interval_minutes()

    assert restored_interval == 7, (
        f"Expected interval 7 from persisted config, got {restored_interval}"
    )

    # build_scheduler must honour that restored interval.
    scheduler = main_mod.build_scheduler(restored_interval)
    job = scheduler.get_job("argus_poll")
    assert job is not None
    # APScheduler IntervalTrigger stores the interval in job.trigger.interval
    import datetime as dt
    assert job.trigger.interval == dt.timedelta(minutes=7), (
        f"Scheduler job interval should be 7 minutes, got {job.trigger.interval}"
    )
