"""Fans out a PowerSnapshot to all registered exporters."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.exporters.base_exporter import BaseExporter
    from src.models.power_snapshot import PowerSnapshot

_LOG = logging.getLogger(__name__)


class DispatchError(Exception):
    """Raised when one or more exporters fail during dispatch."""

    def __init__(self, failures: dict[str, str]) -> None:
        self.failures = failures
        super().__init__(f"Dispatch failed for exporters: {list(failures.keys())}")


class SnapshotDispatcher:
    """Dispatches a PowerSnapshot to all registered exporters."""

    def __init__(self) -> None:
        self._exporters: list["BaseExporter"] = []

    def add_exporter(self, exporter: "BaseExporter") -> None:
        self._exporters.append(exporter)

    def remove_exporter(self, exporter: "BaseExporter") -> None:
        self._exporters.remove(exporter)

    def clear(self) -> None:
        self._exporters.clear()

    def dispatch(self, snapshot: "PowerSnapshot") -> None:
        """Send snapshot to all exporters; raise DispatchError if any fail."""
        failures: dict[str, str] = {}
        for exporter in self._exporters:
            name = type(exporter).__name__
            try:
                exporter.export(snapshot)
            except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                _LOG.exception("Exporter %s failed: %s", name, exc)
                failures[name] = str(exc)
        if failures:
            raise DispatchError(failures)
