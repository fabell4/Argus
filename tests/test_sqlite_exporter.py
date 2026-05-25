"""Integration tests for SQLiteExporter — schema, write, and retention pruning."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from src.exporters.sqlite_exporter import SQLiteExporter
from src.models.power_snapshot import PowerSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_snapshot(
    device_id: str = "nut:ups@localhost",
    device_type: str = "ups",
    power_watts: float = 100.0,
) -> PowerSnapshot:
    return PowerSnapshot(
        timestamp=datetime.now(timezone.utc),
        device_id=device_id,
        device_type=device_type,
        power_watts=power_watts,
    )


def _row_count(db_path: str, table: str = "power_snapshots") -> int:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608


def _insert_snapshot_at(
    db_path: str,
    ts: datetime,
    device_id: str = "nut:ups@localhost",
) -> None:
    """Directly insert a snapshot row with a specific timestamp (bypasses export())."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO power_snapshots (timestamp, device_id, device_type)"
            " VALUES (?, ?, ?)",
            (ts.isoformat(), device_id, "ups"),
        )
        conn.commit()


def _insert_event_at(db_path: str, ts: datetime) -> None:
    """Directly insert an event row with a specific timestamp."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO power_events (timestamp, device_id, event_type, metadata)"
            " VALUES (?, ?, ?, ?)",
            (ts.isoformat(), "nut:ups@localhost", "on_battery", "{}"),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_tables_created(self, tmp_path: pytest.TempPathFactory) -> None:
        db_path = str(tmp_path / "argus.db")
        SQLiteExporter(db_path=db_path)
        with sqlite3.connect(db_path) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        assert "power_snapshots" in tables
        assert "power_events" in tables

    def test_indexes_created(self, tmp_path: pytest.TempPathFactory) -> None:
        db_path = str(tmp_path / "argus.db")
        SQLiteExporter(db_path=db_path)
        with sqlite3.connect(db_path) as conn:
            indexes = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )
            }
        assert "idx_snapshots_timestamp" in indexes
        assert "idx_events_timestamp" in indexes

    def test_wal_mode_enabled(self, tmp_path: pytest.TempPathFactory) -> None:
        db_path = str(tmp_path / "argus.db")
        SQLiteExporter(db_path=db_path)
        with sqlite3.connect(db_path) as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"


# ---------------------------------------------------------------------------
# Export writes
# ---------------------------------------------------------------------------


class TestExport:
    def test_export_writes_row(self, tmp_path: pytest.TempPathFactory) -> None:
        db_path = str(tmp_path / "argus.db")
        exporter = SQLiteExporter(db_path=db_path)
        exporter.export(_make_snapshot())
        assert _row_count(db_path) == 1

    def test_export_persists_all_fields(self, tmp_path: pytest.TempPathFactory) -> None:
        db_path = str(tmp_path / "argus.db")
        exporter = SQLiteExporter(db_path=db_path)
        snap = PowerSnapshot(
            timestamp=datetime.now(timezone.utc),
            device_id="nut:myups@host",
            device_type="ups",
            power_watts=350.0,
            load_percent=70.0,
            voltage=230.0,
            battery_percent=85.0,
            runtime_seconds=1800.0,
            temperature_c=30.5,
            ups_status="OL",
            input_voltage=229.0,
            output_voltage=230.0,
        )
        exporter.export(snap)
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT device_id, power_watts, load_percent, battery_percent,"
                " runtime_seconds, ups_status FROM power_snapshots"
            ).fetchone()
        assert row[0] == "nut:myups@host"
        assert row[1] == 350.0
        assert row[2] == 70.0
        assert row[3] == 85.0
        assert row[4] == 1800.0
        assert row[5] == "OL"

    def test_export_multiple_snapshots(self, tmp_path: pytest.TempPathFactory) -> None:
        db_path = str(tmp_path / "argus.db")
        exporter = SQLiteExporter(db_path=db_path, max_rows=1_000)
        for _ in range(5):
            exporter.export(_make_snapshot())
        assert _row_count(db_path) == 5


# ---------------------------------------------------------------------------
# Prune by age — snapshots
# ---------------------------------------------------------------------------


class TestPruneByAge:
    def test_old_snapshots_pruned(self, tmp_path: pytest.TempPathFactory) -> None:
        """Snapshot older than retention_days is deleted on the next export call."""
        db_path = str(tmp_path / "argus.db")
        exporter = SQLiteExporter(db_path=db_path, retention_days=30)

        old_ts = datetime.now(timezone.utc) - timedelta(days=60)
        _insert_snapshot_at(db_path, old_ts, device_id="old-ups")
        assert _row_count(db_path) == 1

        exporter.export(_make_snapshot(device_id="new-ups"))

        with sqlite3.connect(db_path) as conn:
            remaining_ids = {
                row[0] for row in conn.execute("SELECT device_id FROM power_snapshots")
            }
        assert "old-ups" not in remaining_ids
        assert "new-ups" in remaining_ids

    def test_recent_snapshots_kept(self, tmp_path: pytest.TempPathFactory) -> None:
        """Snapshot newer than retention_days survives the prune."""
        db_path = str(tmp_path / "argus.db")
        exporter = SQLiteExporter(db_path=db_path, retention_days=30)

        recent_ts = datetime.now(timezone.utc) - timedelta(days=5)
        _insert_snapshot_at(db_path, recent_ts)

        exporter.export(_make_snapshot())
        assert _row_count(db_path) == 2

    def test_retention_days_zero_skips_age_prune(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """retention_days=0 disables time-based pruning entirely."""
        db_path = str(tmp_path / "argus.db")
        exporter = SQLiteExporter(db_path=db_path, retention_days=0)

        very_old_ts = datetime.now(timezone.utc) - timedelta(days=1000)
        _insert_snapshot_at(db_path, very_old_ts)

        exporter.export(_make_snapshot())
        assert _row_count(db_path) == 2  # old row kept

    def test_boundary_iso8601_format(self, tmp_path: pytest.TempPathFactory) -> None:
        """Timestamps with T-separator and +00:00 offset are correctly compared.

        Python's datetime.isoformat() produces 'YYYY-MM-DDTHH:MM:SS+00:00'.
        SQLite's datetime('now') produces 'YYYY-MM-DD HH:MM:SS' (space, no tz).
        A plain-text comparison incorrectly treats 'T' (0x54) > ' ' (0x20), so
        a same-day-as-boundary row would never be deleted without the datetime()
        wrapper around the stored timestamp column.
        """
        db_path = str(tmp_path / "argus.db")
        exporter = SQLiteExporter(db_path=db_path, retention_days=30)

        # Place the timestamp 1 hour before the cutoff, on the same calendar day
        # as the cutoff.  Without datetime() normalisation this row is NOT deleted.
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=30)
        boundary_ts = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
        if boundary_ts >= cutoff:
            # Cutoff is already at midnight: move one day earlier to stay "before"
            boundary_ts -= timedelta(days=1)

        _insert_snapshot_at(db_path, boundary_ts, device_id="boundary-ups")
        assert _row_count(db_path) == 1

        exporter.export(_make_snapshot(device_id="new-ups"))

        with sqlite3.connect(db_path) as conn:
            remaining_ids = {
                row[0] for row in conn.execute("SELECT device_id FROM power_snapshots")
            }
        # The boundary row (before the cutoff) must have been pruned
        assert "boundary-ups" not in remaining_ids
        assert "new-ups" in remaining_ids

    def test_sqlite_datetime_t_separator_comparison(self) -> None:
        """Direct unit test: datetime() normalises T+tz before comparison.

        This test is timing-independent and directly verifies the SQLite
        behaviour that motivated the datetime(timestamp) fix in _prune().
        """
        with sqlite3.connect(":memory:") as conn:
            conn.execute("CREATE TABLE t (ts TEXT)")
            # Timestamp with T separator and timezone offset
            conn.execute("INSERT INTO t VALUES (?)", ("2023-10-03T06:00:00+00:00",))
            cutoff = "2023-10-03 12:00:00"

            # Without datetime() wrapper: T (0x54) > space (0x20) → row looks
            # NEWER than the cutoff even though it's actually 6 h earlier.
            plain = conn.execute(
                "SELECT COUNT(*) FROM t WHERE ts < ?", (cutoff,)
            ).fetchone()[0]
            assert plain == 0, (
                "Plain text comparison incorrectly reports row is after cutoff"
            )

            # With datetime() wrapper: ISO 8601 is parsed → correctly < cutoff.
            wrapped = conn.execute(
                "SELECT COUNT(*) FROM t WHERE datetime(ts) < ?", (cutoff,)
            ).fetchone()[0]
            assert wrapped == 1, (
                "datetime() wrapper should expose the row as before the cutoff"
            )


# ---------------------------------------------------------------------------
# Prune by age — events
# ---------------------------------------------------------------------------


class TestPruneEventsByAge:
    def test_old_events_pruned(self, tmp_path: pytest.TempPathFactory) -> None:
        """Events older than retention_days are pruned on the next export."""
        db_path = str(tmp_path / "argus.db")
        exporter = SQLiteExporter(db_path=db_path, retention_days=30)

        old_ts = datetime.now(timezone.utc) - timedelta(days=60)
        _insert_event_at(db_path, old_ts)
        assert _row_count(db_path, "power_events") == 1

        exporter.export(_make_snapshot())
        assert _row_count(db_path, "power_events") == 0

    def test_recent_events_kept(self, tmp_path: pytest.TempPathFactory) -> None:
        """Events newer than retention_days are not pruned."""
        db_path = str(tmp_path / "argus.db")
        exporter = SQLiteExporter(db_path=db_path, retention_days=30)

        recent_ts = datetime.now(timezone.utc) - timedelta(days=5)
        _insert_event_at(db_path, recent_ts)

        exporter.export(_make_snapshot())
        assert _row_count(db_path, "power_events") == 1

    def test_retention_zero_skips_event_age_prune(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """retention_days=0 leaves old events untouched."""
        db_path = str(tmp_path / "argus.db")
        exporter = SQLiteExporter(db_path=db_path, retention_days=0)

        very_old_ts = datetime.now(timezone.utc) - timedelta(days=1000)
        _insert_event_at(db_path, very_old_ts)

        exporter.export(_make_snapshot())
        assert _row_count(db_path, "power_events") == 1


# ---------------------------------------------------------------------------
# Prune by max_rows — snapshots
# ---------------------------------------------------------------------------


class TestPruneByMaxRows:
    def test_excess_rows_removed_to_max(self, tmp_path: pytest.TempPathFactory) -> None:
        """After export, row count must not exceed max_rows."""
        db_path = str(tmp_path / "argus.db")
        max_rows = 5
        exporter = SQLiteExporter(db_path=db_path, retention_days=0, max_rows=max_rows)

        base = datetime.now(timezone.utc) - timedelta(hours=10)
        for i in range(10):
            _insert_snapshot_at(db_path, base + timedelta(hours=i), device_id=f"ups{i}")

        exporter.export(_make_snapshot(device_id="ups_new"))

        assert _row_count(db_path) == max_rows

    def test_oldest_rows_removed_first(self, tmp_path: pytest.TempPathFactory) -> None:
        """When rows are culled for max_rows, the oldest timestamps are removed first."""
        db_path = str(tmp_path / "argus.db")
        max_rows = 3
        exporter = SQLiteExporter(db_path=db_path, retention_days=0, max_rows=max_rows)

        base = datetime.now(timezone.utc) - timedelta(hours=10)
        for i in range(5):
            _insert_snapshot_at(db_path, base + timedelta(hours=i), device_id=f"ups{i}")

        # Exporting adds ups_new (→ 6 rows), then prune culls 3 oldest: ups0, ups1, ups2
        exporter.export(_make_snapshot(device_id="ups_new"))

        assert _row_count(db_path) == max_rows
        with sqlite3.connect(db_path) as conn:
            remaining = {
                row[0] for row in conn.execute("SELECT device_id FROM power_snapshots")
            }
        assert "ups0" not in remaining
        assert "ups1" not in remaining
        assert "ups2" not in remaining
        assert "ups3" in remaining
        assert "ups4" in remaining
        assert "ups_new" in remaining

    def test_count_at_exact_max_rows_not_culled(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Exactly max_rows rows are acceptable — no further culling occurs."""
        db_path = str(tmp_path / "argus.db")
        max_rows = 5
        exporter = SQLiteExporter(db_path=db_path, retention_days=0, max_rows=max_rows)

        base = datetime.now(timezone.utc) - timedelta(hours=5)
        for i in range(max_rows - 1):
            _insert_snapshot_at(db_path, base + timedelta(hours=i))

        # This export brings count to exactly max_rows → no deletion
        exporter.export(_make_snapshot())
        assert _row_count(db_path) == max_rows

    def test_max_rows_combined_with_age_prune(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Age prune fires first; max_rows check operates on the post-age count."""
        db_path = str(tmp_path / "argus.db")
        max_rows = 3
        exporter = SQLiteExporter(db_path=db_path, retention_days=30, max_rows=max_rows)

        # 3 old rows (will be age-pruned) + 4 recent rows (will remain)
        old_ts = datetime.now(timezone.utc) - timedelta(days=60)
        for i in range(3):
            _insert_snapshot_at(
                db_path, old_ts + timedelta(hours=i), device_id=f"old{i}"
            )

        recent_base = datetime.now(timezone.utc) - timedelta(hours=4)
        for i in range(4):
            _insert_snapshot_at(
                db_path, recent_base + timedelta(hours=i), device_id=f"recent{i}"
            )

        # After age-prune: 4 recent rows remain.
        # Export adds 1 more (5 total) → max_rows=3 culls 2 oldest.
        exporter.export(_make_snapshot(device_id="newest"))

        assert _row_count(db_path) == max_rows

        with sqlite3.connect(db_path) as conn:
            remaining = {
                row[0] for row in conn.execute("SELECT device_id FROM power_snapshots")
            }
        # All old rows must be gone (age-pruned)
        for i in range(3):
            assert f"old{i}" not in remaining
        # The very newest row must survive
        assert "newest" in remaining
