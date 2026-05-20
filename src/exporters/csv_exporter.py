"""CSV exporter — appends one row per PowerSnapshot to a rotating CSV file."""
from __future__ import annotations

import csv
import glob
import logging
import os
import threading
from datetime import datetime, timezone

from src.exporters.base_exporter import BaseExporter
from src.models.power_snapshot import PowerSnapshot

_LOG = logging.getLogger(__name__)

_FIELDNAMES = [
    "timestamp",
    "device_id",
    "device_type",
    "power_watts",
    "load_percent",
    "voltage",
    "battery_percent",
    "runtime_seconds",
    "current_amps",
    "frequency_hz",
    "temperature_c",
    "ups_status",
    "input_voltage",
    "output_voltage",
    "outlet_count",
]


class CSVExporter(BaseExporter):
    """Appends one row per snapshot to a rotating CSV file.

    Rotation happens when the current file exceeds *max_size_mb*.
    Rotated files are named ``<base>.<YYYYMMDD-HHMMSS>.csv`` and are
    pruned when they are older than *retention_days*.
    """

    def __init__(
        self,
        path: str = "data/argus.csv",
        max_size_mb: float = 10.0,
        retention_days: int = 30,
    ) -> None:
        self._path = path
        self._max_bytes = int(max_size_mb * 1024 * 1024)
        self._retention_days = retention_days
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)

    # ------------------------------------------------------------------
    # BaseExporter
    # ------------------------------------------------------------------

    def export(self, snapshot: PowerSnapshot) -> None:
        with self._lock:
            self._rotate_if_needed()
            self._write_row(snapshot)
            self._prune_old_files()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_row(self, snapshot: PowerSnapshot) -> None:
        """Append one CSV row, writing the header first if the file is new."""
        needs_header = not os.path.exists(self._path) or os.path.getsize(self._path) == 0
        with open(self._path, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=_FIELDNAMES)
            if needs_header:
                writer.writeheader()
            writer.writerow(
                {
                    "timestamp": snapshot.timestamp.isoformat(),
                    "device_id": snapshot.device_id,
                    "device_type": snapshot.device_type,
                    "power_watts": snapshot.power_watts,
                    "load_percent": snapshot.load_percent,
                    "voltage": snapshot.voltage,
                    "battery_percent": snapshot.battery_percent,
                    "runtime_seconds": snapshot.runtime_seconds,
                    "current_amps": snapshot.current_amps,
                    "frequency_hz": snapshot.frequency_hz,
                    "temperature_c": snapshot.temperature_c,
                    "ups_status": snapshot.ups_status,
                    "input_voltage": snapshot.input_voltage,
                    "output_voltage": snapshot.output_voltage,
                    "outlet_count": snapshot.outlet_count,
                }
            )

    def _rotate_if_needed(self) -> None:
        """Rename the active file to a timestamped archive when it exceeds the size limit."""
        if not os.path.exists(self._path):
            return
        if self._max_bytes <= 0:
            return
        if os.path.getsize(self._path) < self._max_bytes:
            return

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        base, ext = os.path.splitext(self._path)
        rotated = f"{base}.{stamp}{ext}"
        os.rename(self._path, rotated)
        _LOG.info("CSV rotated: %s → %s", self._path, rotated)

    def _prune_old_files(self) -> None:
        """Delete rotated files older than *retention_days*."""
        if self._retention_days <= 0:
            return
        base, ext = os.path.splitext(self._path)
        pattern = f"{base}.*{ext}"
        cutoff = datetime.now(timezone.utc).timestamp() - self._retention_days * 86400
        for path in glob.glob(pattern):
            if path == self._path:
                continue
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
                    _LOG.info("Pruned old CSV archive: %s", path)
            except OSError as exc:
                _LOG.warning("Could not prune CSV file %s: %s", path, exc)
