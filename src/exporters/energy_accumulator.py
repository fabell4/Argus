"""Energy accumulator exporter — tracks cumulative kWh per device.

Uses trapezoidal integration (power_watts × Δt) between consecutive snapshots.
Persists per-device cumulative energy in a separate SQLite table so totals
survive process restarts.  Optionally exposes a Prometheus counter and
cost estimation when ENERGY_RATE_PER_KWH is set.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
from datetime import datetime

from src.exporters.base_exporter import BaseExporter
from src.models.power_snapshot import PowerSnapshot

_LOG = logging.getLogger(__name__)

_CREATE_ENERGY_TABLE = """
CREATE TABLE IF NOT EXISTS energy_accumulation (
    device_id           TEXT PRIMARY KEY,
    energy_wh_total     REAL NOT NULL DEFAULT 0.0,
    last_updated        TEXT NOT NULL
)
"""


class EnergyAccumulatorExporter(BaseExporter):
    """Accumulates watt-hours per device using trapezoidal integration.

    On each :meth:`export` call the incremental energy since the last snapshot
    is computed as ``power_watts × Δt`` (hours) and added to the running total
    stored in SQLite.  A Prometheus counter is updated if *prometheus_client*
    is installed and the metric has been registered.
    """

    def __init__(
        self,
        db_path: str = "data/argus.db",
        rate_per_kwh: float = 0.0,
    ) -> None:
        self._db_path = db_path
        self._rate_per_kwh = rate_per_kwh
        self._lock = threading.Lock()
        # device_id → last snapshot (for Δt computation)
        self._last: dict[str, PowerSnapshot] = {}
        self._init_db()
        self._counter: object | None = None
        self._init_prometheus()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._connect() as conn:
            conn.execute(_CREATE_ENERGY_TABLE)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, check_same_thread=False, timeout=30)

    def _init_prometheus(self) -> None:
        try:
            from prometheus_client import Counter  # type: ignore[import-untyped]

            self._counter = Counter(
                "argus_energy_kwh_total",
                "Cumulative energy consumed in kilowatt-hours",
                ["device_id"],
            )
        except ImportError:
            _LOG.debug("prometheus_client not installed; energy kWh counter disabled.")

    # ------------------------------------------------------------------
    # BaseExporter
    # ------------------------------------------------------------------

    def export(self, snapshot: PowerSnapshot) -> None:
        if snapshot.power_watts is None:
            self._last[snapshot.device_id] = snapshot
            return

        with self._lock:
            prev = self._last.get(snapshot.device_id)
            increment_wh = 0.0
            if prev is not None and prev.power_watts is not None:
                # Trapezoidal integration: average power × elapsed hours
                avg_watts = (prev.power_watts + snapshot.power_watts) / 2.0
                delta_s = (
                    snapshot.timestamp - prev.timestamp
                ).total_seconds()
                if delta_s > 0:
                    increment_wh = avg_watts * (delta_s / 3600.0)

            self._last[snapshot.device_id] = snapshot

            if increment_wh > 0:
                self._persist(snapshot.device_id, increment_wh, snapshot.timestamp)

    # ------------------------------------------------------------------
    # Persistence & Prometheus
    # ------------------------------------------------------------------

    def _persist(
        self, device_id: str, increment_wh: float, timestamp: datetime
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO energy_accumulation (device_id, energy_wh_total, last_updated)
                VALUES (?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    energy_wh_total = energy_wh_total + excluded.energy_wh_total,
                    last_updated = excluded.last_updated
                """,
                (device_id, increment_wh, timestamp.isoformat()),
            )
            conn.commit()

        if self._counter is not None:
            increment_kwh = increment_wh / 1000.0
            labels = self._counter.labels(device_id=device_id)  # type: ignore[attr-defined]
            labels.inc(increment_kwh)

    # ------------------------------------------------------------------
    # Query helpers (used by GET /api/energy)
    # ------------------------------------------------------------------

    def get_totals(self) -> list[dict[str, object]]:
        """Return cumulative energy totals for all devices."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT device_id, energy_wh_total, last_updated FROM energy_accumulation"
            ).fetchall()
        result = []
        for device_id, energy_wh, last_updated in rows:
            entry: dict[str, object] = {
                "device_id": device_id,
                "energy_wh": energy_wh,
                "energy_kwh": energy_wh / 1000.0,
                "last_updated": last_updated,
            }
            if self._rate_per_kwh > 0:
                entry["estimated_cost"] = (energy_wh / 1000.0) * self._rate_per_kwh
            result.append(entry)
        return result
