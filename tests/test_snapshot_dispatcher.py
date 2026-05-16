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
    dispatcher = SnapshotDispatcher()
    bad_exporter = MagicMock()
    bad_exporter.export.side_effect = RuntimeError("boom")
    dispatcher.add_exporter(bad_exporter)

    with pytest.raises(DispatchError) as exc_info:
        dispatcher.dispatch(_snapshot())

    assert "MagicMock" in exc_info.value.failures


def test_dispatch_empty_does_nothing() -> None:
    dispatcher = SnapshotDispatcher()
    dispatcher.dispatch(_snapshot())  # no error


def test_clear_removes_all_exporters() -> None:
    dispatcher = SnapshotDispatcher()
    dispatcher.add_exporter(MagicMock())
    dispatcher.clear()
    dispatcher.dispatch(_snapshot())  # still no error, no calls
