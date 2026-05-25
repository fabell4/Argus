"""Tests for SnapshotDispatcher."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.models.power_snapshot import PowerSnapshot
from src.snapshot_dispatcher import DispatchError, SnapshotDispatcher


def _snapshot() -> PowerSnapshot:
    return PowerSnapshot(
        timestamp=datetime.now(timezone.utc),
        device_id="nut:ups@localhost",
        device_type="ups",
        power_watts=100.0,
    )


def test_dispatch_calls_all_exporters() -> None:
    """dispatch calls export on all registered exporters."""
    dispatcher = SnapshotDispatcher()
    exporter_a = MagicMock()
    exporter_b = MagicMock()
    dispatcher.add_exporter(exporter_a)
    dispatcher.add_exporter(exporter_b)

    snap = _snapshot()
    dispatcher.dispatch(snap)

    exporter_a.export.assert_called_once_with(snap)
    exporter_b.export.assert_called_once_with(snap)


def test_dispatch_raises_on_exporter_failure() -> None:
    """dispatch raises DispatchError when an exporter raises."""
    dispatcher = SnapshotDispatcher()
    bad_exporter = MagicMock()
    bad_exporter.export.side_effect = RuntimeError("boom")
    dispatcher.add_exporter(bad_exporter)

    with pytest.raises(DispatchError) as exc_info:
        dispatcher.dispatch(_snapshot())

    assert "MagicMock" in exc_info.value.failures


def test_dispatch_empty_does_nothing() -> None:
    """dispatch with no exporters registered completes without error."""
    dispatcher = SnapshotDispatcher()
    dispatcher.dispatch(_snapshot())  # no error


def test_clear_removes_all_exporters() -> None:
    """clear removes all exporters so subsequent dispatch calls succeed silently."""
    dispatcher = SnapshotDispatcher()
    dispatcher.add_exporter(MagicMock())
    dispatcher.clear()
    dispatcher.dispatch(_snapshot())  # still no error, no calls


def test_remove_exporter_stops_export_calls() -> None:
    """remove_exporter removes a specific exporter so it is no longer called."""
    dispatcher = SnapshotDispatcher()
    exporter = MagicMock()
    dispatcher.add_exporter(exporter)
    dispatcher.remove_exporter(exporter)
    dispatcher.dispatch(_snapshot())
    exporter.export.assert_not_called()


def test_partial_failure_raises_dispatch_error_with_remaining_called() -> None:
    """When one exporter fails the others still run and DispatchError is raised."""
    dispatcher = SnapshotDispatcher()
    good_exporter = MagicMock()
    bad_exporter = MagicMock()
    bad_exporter.export.side_effect = RuntimeError("disk full")
    dispatcher.add_exporter(good_exporter)
    dispatcher.add_exporter(bad_exporter)

    snap = _snapshot()
    with pytest.raises(DispatchError) as exc_info:
        dispatcher.dispatch(snap)

    good_exporter.export.assert_called_once_with(snap)
    assert len(exc_info.value.failures) == 1
