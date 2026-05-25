"""Tests for CSVExporter — file creation, append, rotation, pruning."""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.exporters.csv_exporter import CSVExporter
from src.models.power_snapshot import PowerSnapshot


def _snap(
    device_id: str = "nut:ups@localhost", power_watts: float = 100.0
) -> PowerSnapshot:
    return PowerSnapshot(
        timestamp=datetime.now(timezone.utc),
        device_id=device_id,
        device_type="ups",
        power_watts=power_watts,
    )


# ---------------------------------------------------------------------------
# File creation and header
# ---------------------------------------------------------------------------


def test_export_creates_csv_file(tmp_path: Path) -> None:
    path = str(tmp_path / "argus.csv")
    exporter = CSVExporter(path=path)
    exporter.export(_snap())
    assert os.path.exists(path)


def test_export_writes_header_on_first_write(tmp_path: Path) -> None:
    path = str(tmp_path / "argus.csv")
    exporter = CSVExporter(path=path)
    exporter.export(_snap())
    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames is not None
        assert "timestamp" in reader.fieldnames
        assert "device_id" in reader.fieldnames
        assert "power_watts" in reader.fieldnames


def test_export_does_not_duplicate_header(tmp_path: Path) -> None:
    path = str(tmp_path / "argus.csv")
    exporter = CSVExporter(path=path)
    exporter.export(_snap())
    exporter.export(_snap())
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    header_count = sum(
        1 for line in lines if "timestamp" in line and "device_id" in line
    )
    assert header_count == 1


def test_export_appends_rows(tmp_path: Path) -> None:
    path = str(tmp_path / "argus.csv")
    exporter = CSVExporter(path=path)
    exporter.export(_snap())
    exporter.export(_snap())
    exporter.export(_snap())
    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    assert len(rows) == 3


def test_export_writes_correct_device_id(tmp_path: Path) -> None:
    path = str(tmp_path / "argus.csv")
    exporter = CSVExporter(path=path)
    exporter.export(_snap(device_id="snmp:pdu@10.0.0.1"))
    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        row = next(reader)
    assert row["device_id"] == "snmp:pdu@10.0.0.1"


def test_export_writes_power_watts(tmp_path: Path) -> None:
    path = str(tmp_path / "argus.csv")
    exporter = CSVExporter(path=path)
    exporter.export(_snap(power_watts=250.5))
    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        row = next(reader)
    assert float(row["power_watts"]) == pytest.approx(250.5)


# ---------------------------------------------------------------------------
# Missing directory
# ---------------------------------------------------------------------------


def test_export_creates_missing_directory(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "nested"
    path = str(nested / "argus.csv")
    exporter = CSVExporter(path=path)
    exporter.export(_snap())
    assert os.path.exists(path)


# ---------------------------------------------------------------------------
# Size-based rotation
# ---------------------------------------------------------------------------


def test_export_rotates_when_file_exceeds_max_size(tmp_path: Path) -> None:
    path = str(tmp_path / "argus.csv")
    # Set tiny max size (1 byte) so any write triggers rotation
    exporter = CSVExporter(path=path, max_size_mb=0.000001)
    exporter.export(_snap())  # writes file
    exporter.export(_snap())  # should rotate the first file
    # Original path should still exist (new file), and there should be a rotated archive
    files = list(tmp_path.glob("*.csv"))
    assert len(files) >= 2


def test_export_no_rotation_when_disabled(tmp_path: Path) -> None:
    path = str(tmp_path / "argus.csv")
    exporter = CSVExporter(path=path, max_size_mb=0)  # disabled
    for _ in range(5):
        exporter.export(_snap())
    files = list(tmp_path.glob("*.csv"))
    assert len(files) == 1


# ---------------------------------------------------------------------------
# Age-based pruning
# ---------------------------------------------------------------------------


def test_prune_skips_active_file(tmp_path: Path) -> None:
    path = str(tmp_path / "argus.csv")
    exporter = CSVExporter(path=path, retention_days=1)
    exporter.export(_snap())
    # Active file must survive pruning
    assert os.path.exists(path)


def test_prune_does_not_run_when_retention_zero(tmp_path: Path) -> None:
    path = str(tmp_path / "argus.csv")
    exporter = CSVExporter(path=path, retention_days=0)
    exporter.export(_snap())
    assert os.path.exists(path)
