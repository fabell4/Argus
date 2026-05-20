"""SQLite exporter — primary authoritative store for Argus telemetry."""
from __future__ import annotations

import logging
import os
import sqlite3
import threading

from src.exporters.base_exporter import BaseExporter
from src.models.power_snapshot import PowerSnapshot

_LOG = logging.getLogger(__name__)

_CREATE_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS power_snapshots (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp        TEXT NOT NULL,
    device_id        TEXT NOT NULL,
    device_type      TEXT NOT NULL,
    power_watts      REAL,
    load_percent     REAL,
    voltage          REAL,
    battery_percent  REAL,
    runtime_seconds  REAL,
    current_amps     REAL,
    frequency_hz     REAL,
    temperature_c    REAL,
    ups_status       TEXT,
    input_voltage    REAL,
    output_voltage   REAL,
    outlet_count     INTEGER
)
"""

_CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS power_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    device_id   TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    metadata    TEXT NOT NULL DEFAULT '{}'
)
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON power_snapshots(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON power_events(timestamp)",
]

_INSERT_SNAPSHOT = """
INSERT INTO power_snapshots (
    timestamp, device_id, device_type,
    power_watts, load_percent, voltage, battery_percent, runtime_seconds,
    current_amps, frequency_hz, temperature_c,
    ups_status, input_voltage, output_voltage, outlet_count
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


class SQLiteExporter(BaseExporter):
    """Stores PowerSnapshot rows in a local SQLite database."""

    def __init__(
        self,
        db_path: str = "data/argus.db",
        retention_days: int = 90,
        max_rows: int = 100_000,
    ) -> None:
        self._db_path = db_path
        self._retention_days = retention_days
        self._max_rows = max_rows
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._connect() as conn:
            conn.execute(_CREATE_SNAPSHOTS)
            conn.execute(_CREATE_EVENTS)
            conn.execute("PRAGMA journal_mode=WAL")
            for stmt in _CREATE_INDEXES:
                conn.execute(stmt)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, check_same_thread=False)

    def export(self, snapshot: PowerSnapshot) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                _INSERT_SNAPSHOT,
                (
                    snapshot.timestamp.isoformat(),
                    snapshot.device_id,
                    snapshot.device_type,
                    snapshot.power_watts,
                    snapshot.load_percent,
                    snapshot.voltage,
                    snapshot.battery_percent,
                    snapshot.runtime_seconds,
                    snapshot.current_amps,
                    snapshot.frequency_hz,
                    snapshot.temperature_c,
                    snapshot.ups_status,
                    snapshot.input_voltage,
                    snapshot.output_voltage,
                    snapshot.outlet_count,
                ),
            )
            conn.commit()
        self._prune()

    def _prune(self) -> None:
        with self._lock, self._connect() as conn:
            if self._retention_days > 0:
                cutoff = (f"-{self._retention_days} days",)
                # datetime(timestamp) normalises the stored ISO-8601 value
                # (which contains a 'T' separator and '+00:00' offset) to
                # SQLite's 'YYYY-MM-DD HH:MM:SS' format before comparison.
                # A plain text compare would incorrectly treat 'T' > ' ',
                # causing same-day-as-boundary rows to survive deletion.
                conn.execute(
                    "DELETE FROM power_snapshots"
                    " WHERE datetime(timestamp) < datetime('now', ?)",
                    cutoff,
                )
                conn.execute(
                    "DELETE FROM power_events"
                    " WHERE datetime(timestamp) < datetime('now', ?)",
                    cutoff,
                )
            row = conn.execute("SELECT COUNT(*) FROM power_snapshots").fetchone()
            count = row[0] if row else 0
            if count > self._max_rows:
                excess = count - self._max_rows
                conn.execute(
                    "DELETE FROM power_snapshots WHERE id IN "
                    "(SELECT id FROM power_snapshots ORDER BY timestamp ASC LIMIT ?)",
                    (excess,),
                )
            conn.commit()
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self._vacuum_if_fragmented(conn)

    def _vacuum_if_fragmented(self, conn: sqlite3.Connection) -> None:
        """Run VACUUM when free-page ratio exceeds 20% of total page count."""
        row = conn.execute("PRAGMA freelist_count").fetchone()
        free = row[0] if row else 0
        row = conn.execute("PRAGMA page_count").fetchone()
        total = row[0] if row else 1
        if total > 0 and (free / total) > 0.20:
            _LOG.info(
                "SQLite fragmentation %.1f%% (free=%d / total=%d); running VACUUM.",
                100.0 * free / total,
                free,
                total,
            )
            # VACUUM cannot run inside a transaction; use autocommit isolation.
            conn.isolation_level = None
            conn.execute("VACUUM")
            conn.isolation_level = ""

    def get_db_path(self) -> str:
        return self._db_path
