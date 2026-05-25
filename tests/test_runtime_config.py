"""Tests for RuntimeConfig — validation, atomic write, cache, edge cases."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src import runtime_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_path(tmp_path: Path) -> "pytest.MonkeyPatch":
    """Return a context-free patch. Use as a context manager in tests."""
    return patch.object(
        runtime_config, "_CONFIG_PATH", str(tmp_path / "runtime_config.json")
    )


# ---------------------------------------------------------------------------
# load() returns defaults when file absent
# ---------------------------------------------------------------------------


def test_load_returns_defaults_when_no_file(tmp_path: Path) -> None:
    with patch.object(
        runtime_config, "_CONFIG_PATH", str(tmp_path / "runtime_config.json")
    ):
        data = runtime_config.load()
    assert "poll_interval_minutes" in data
    assert "enabled_exporters" in data


def test_load_merges_file_with_defaults(tmp_path: Path) -> None:
    cfg_path = tmp_path / "runtime_config.json"
    cfg_path.write_text(json.dumps({"poll_interval_minutes": 15}), encoding="utf-8")
    with patch.object(runtime_config, "_CONFIG_PATH", str(cfg_path)):
        data = runtime_config.load()
    assert data["poll_interval_minutes"] == 15
    assert "enabled_exporters" in data  # from defaults


def test_load_resets_to_defaults_on_corrupt_json(tmp_path: Path) -> None:
    cfg_path = tmp_path / "runtime_config.json"
    cfg_path.write_text("NOT VALID JSON {{", encoding="utf-8")
    with patch.object(runtime_config, "_CONFIG_PATH", str(cfg_path)):
        data = runtime_config.load()
    assert "poll_interval_minutes" in data


# ---------------------------------------------------------------------------
# save() performs atomic write
# ---------------------------------------------------------------------------


def test_save_creates_file(tmp_path: Path) -> None:
    cfg_path = tmp_path / "runtime_config.json"
    with (
        patch.object(runtime_config, "_CONFIG_PATH", str(cfg_path)),
        patch.object(runtime_config, "_save_raw", wraps=runtime_config._save_raw),
    ):
        runtime_config.save({"poll_interval_minutes": 5})
    assert cfg_path.exists()
    loaded = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert loaded["poll_interval_minutes"] == 5


def test_save_is_idempotent(tmp_path: Path) -> None:
    cfg_path = tmp_path / "runtime_config.json"
    with patch.object(runtime_config, "_CONFIG_PATH", str(cfg_path)):
        runtime_config.save({"poll_interval_minutes": 7})
        runtime_config.save({"poll_interval_minutes": 7})
    loaded = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert loaded["poll_interval_minutes"] == 7


# ---------------------------------------------------------------------------
# get_interval_minutes / set_interval_minutes
# ---------------------------------------------------------------------------


def test_set_and_get_interval(tmp_path: Path) -> None:
    with patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")):
        runtime_config.set_interval_minutes(10)
        assert runtime_config.get_interval_minutes() == 10


def test_set_interval_rejects_zero(tmp_path: Path) -> None:
    with patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")):
        with pytest.raises(ValueError):
            runtime_config.set_interval_minutes(0)


def test_set_interval_rejects_negative(tmp_path: Path) -> None:
    with patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")):
        with pytest.raises(ValueError):
            runtime_config.set_interval_minutes(-1)


# ---------------------------------------------------------------------------
# get_enabled_exporters / set_enabled_exporters
# ---------------------------------------------------------------------------


def test_set_and_get_enabled_exporters(tmp_path: Path) -> None:
    with patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")):
        runtime_config.set_enabled_exporters(["sqlite", "prometheus"])
        exporters = runtime_config.get_enabled_exporters()
    assert "sqlite" in exporters
    assert "prometheus" in exporters


def test_set_enabled_exporters_rejects_unknown(tmp_path: Path) -> None:
    with patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")):
        with pytest.raises(ValueError):
            runtime_config.set_enabled_exporters(["sqlite", "unknown_exporter_xyz"])


# ---------------------------------------------------------------------------
# Scheduler paused
# ---------------------------------------------------------------------------


def test_set_scheduler_paused(tmp_path: Path) -> None:
    with patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")):
        runtime_config.set_scheduler_paused(True)
        assert runtime_config.get_scheduler_paused() is True
        runtime_config.set_scheduler_paused(False)
        assert runtime_config.get_scheduler_paused() is False


# ---------------------------------------------------------------------------
# Alert config
# ---------------------------------------------------------------------------


def test_get_alert_config_returns_empty_by_default(tmp_path: Path) -> None:
    with patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")):
        cfg = runtime_config.get_alert_config()
    assert isinstance(cfg, dict)


def test_alert_config_persisted_via_save(tmp_path: Path) -> None:
    cfg_path = tmp_path / "rc.json"
    with patch.object(runtime_config, "_CONFIG_PATH", str(cfg_path)):
        data = runtime_config.load()
        data["alert_config"] = {"alert_on_battery": False}
        runtime_config.save(data)
        loaded = runtime_config.load()
    assert loaded["alert_config"]["alert_on_battery"] is False


# ---------------------------------------------------------------------------
# Poll trigger sentinel
# ---------------------------------------------------------------------------


def test_consume_poll_trigger_returns_false_when_no_sentinel(tmp_path: Path) -> None:
    with (
        patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")),
        patch.object(runtime_config, "_RUN_TRIGGER", str(tmp_path / ".run_trigger")),
    ):
        assert runtime_config.consume_poll_trigger() is False


def test_consume_poll_trigger_returns_true_and_removes_file(tmp_path: Path) -> None:
    trigger = tmp_path / ".run_trigger"
    trigger.touch()
    with (
        patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")),
        patch.object(runtime_config, "_RUN_TRIGGER", str(trigger)),
    ):
        assert runtime_config.consume_poll_trigger() is True
        assert not trigger.exists()


# ---------------------------------------------------------------------------
# mark_running / mark_done / is_running
# ---------------------------------------------------------------------------


def test_mark_running_creates_sentinel(tmp_path: Path) -> None:
    sentinel = tmp_path / ".running"
    with (
        patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")),
        patch.object(runtime_config, "_RUNNING_SENTINEL", str(sentinel)),
    ):
        runtime_config.mark_running()
        assert sentinel.exists()


def test_mark_done_removes_sentinel(tmp_path: Path) -> None:
    sentinel = tmp_path / ".running"
    sentinel.touch()
    with (
        patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")),
        patch.object(runtime_config, "_RUNNING_SENTINEL", str(sentinel)),
    ):
        runtime_config.mark_done()
        assert not sentinel.exists()


def test_mark_done_is_idempotent_when_no_sentinel(tmp_path: Path) -> None:
    sentinel = tmp_path / ".running"
    with (
        patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")),
        patch.object(runtime_config, "_RUNNING_SENTINEL", str(sentinel)),
    ):
        runtime_config.mark_done()  # should not raise


def test_is_running_true_when_sentinel_exists(tmp_path: Path) -> None:
    sentinel = tmp_path / ".running"
    sentinel.touch()
    with patch.object(runtime_config, "_RUNNING_SENTINEL", str(sentinel)):
        assert runtime_config.is_running() is True


def test_is_running_false_when_no_sentinel(tmp_path: Path) -> None:
    sentinel = tmp_path / ".running"
    with patch.object(runtime_config, "_RUNNING_SENTINEL", str(sentinel)):
        assert runtime_config.is_running() is False


# ---------------------------------------------------------------------------
# Timestamps — next_poll_at / last_poll_at
# ---------------------------------------------------------------------------


def test_set_and_get_next_poll_at(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    dt = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    with patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")):
        runtime_config.set_next_poll_at(dt)
        result = runtime_config.get_next_poll_at()
    assert result is not None
    assert "2026-06-01" in result


def test_set_next_poll_at_none_clears_value(tmp_path: Path) -> None:
    with patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")):
        runtime_config.set_next_poll_at(None)
        result = runtime_config.get_next_poll_at()
    assert result is None


def test_set_and_get_last_poll_at(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    dt = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    with patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")):
        runtime_config.set_last_poll_at(dt)
        result = runtime_config.get_last_poll_at()
    assert result is not None
    assert "2026-06-01" in result


# ---------------------------------------------------------------------------
# alert_config get/set
# ---------------------------------------------------------------------------


def test_set_and_get_alert_config(tmp_path: Path) -> None:
    cfg = {"failure_threshold": 3, "cooldown_seconds": 60}
    with patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")):
        runtime_config.set_alert_config(cfg)
        result = runtime_config.get_alert_config()
    assert result == cfg


def test_set_alert_config_rejects_non_dict(tmp_path: Path) -> None:
    with patch.object(runtime_config, "_CONFIG_PATH", str(tmp_path / "rc.json")):
        with pytest.raises(ValueError):
            runtime_config.set_alert_config("not-a-dict")  # type: ignore[arg-type]
