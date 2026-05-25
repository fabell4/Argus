"""Tests for EnergyAccumulatorExporter — watt-hour calculation, cumulative storage, cost."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.exporters.energy_accumulator import EnergyAccumulatorExporter
from src.models.power_snapshot import PowerSnapshot


def _snap(
    device_id: str = "nut:ups@localhost",
    power_watts: float | None = 100.0,
    offset_seconds: int = 0,
) -> PowerSnapshot:
    return PowerSnapshot(
        timestamp=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        + timedelta(seconds=offset_seconds),
        device_id=device_id,
        device_type="ups",
        power_watts=power_watts,
    )


def _exporter(db_path: str, **kwargs: object) -> EnergyAccumulatorExporter:
    """Create an EnergyAccumulatorExporter with Prometheus disabled for isolation."""
    with patch.object(EnergyAccumulatorExporter, "_init_prometheus", lambda self: None):
        exp = EnergyAccumulatorExporter(db_path=db_path, **kwargs)  # type: ignore[arg-type]
    return exp


# ---------------------------------------------------------------------------
# Watt-hour calculation
# ---------------------------------------------------------------------------

def test_first_snapshot_records_no_energy(tmp_path: Path) -> None:
    db = str(tmp_path / "argus.db")
    exporter = _exporter(db)
    exporter.export(_snap())
    assert exporter.get_totals() == []


def test_two_snapshots_accumulates_wh(tmp_path: Path) -> None:
    db = str(tmp_path / "argus.db")
    exporter = _exporter(db)
    # 100 W for 3600 seconds = 100 Wh
    exporter.export(_snap(power_watts=100.0, offset_seconds=0))
    exporter.export(_snap(power_watts=100.0, offset_seconds=3600))
    totals = exporter.get_totals()
    assert len(totals) == 1
    assert totals[0]["energy_wh"] == pytest.approx(100.0)


def test_trapezoidal_integration_with_varying_watts(tmp_path: Path) -> None:
    db = str(tmp_path / "argus.db")
    exporter = _exporter(db)
    # 0 W → 200 W over 3600 seconds: average = 100 W → 100 Wh
    exporter.export(_snap(power_watts=0.0, offset_seconds=0))
    exporter.export(_snap(power_watts=200.0, offset_seconds=3600))
    totals = exporter.get_totals()
    assert totals[0]["energy_wh"] == pytest.approx(100.0)


def test_multiple_exports_accumulate_correctly(tmp_path: Path) -> None:
    db = str(tmp_path / "argus.db")
    exporter = _exporter(db)
    # Three 1-hour intervals at 100 W → 300 Wh total
    exporter.export(_snap(power_watts=100.0, offset_seconds=0))
    exporter.export(_snap(power_watts=100.0, offset_seconds=3600))
    exporter.export(_snap(power_watts=100.0, offset_seconds=7200))
    exporter.export(_snap(power_watts=100.0, offset_seconds=10800))
    totals = exporter.get_totals()
    assert totals[0]["energy_wh"] == pytest.approx(300.0)


def test_snapshot_without_power_watts_skips_accumulation(tmp_path: Path) -> None:
    db = str(tmp_path / "argus.db")
    exporter = _exporter(db)
    exporter.export(_snap(power_watts=None, offset_seconds=0))
    exporter.export(_snap(power_watts=None, offset_seconds=3600))
    assert exporter.get_totals() == []


def test_zero_delta_time_produces_no_energy(tmp_path: Path) -> None:
    db = str(tmp_path / "argus.db")
    exporter = _exporter(db)
    same_ts = _snap(power_watts=1000.0, offset_seconds=0)
    exporter.export(same_ts)
    exporter.export(same_ts)  # same timestamp → delta_s = 0
    assert exporter.get_totals() == []


# ---------------------------------------------------------------------------
# Cumulative storage survives re-instantiation
# ---------------------------------------------------------------------------

def test_energy_persists_across_exporter_instances(tmp_path: Path) -> None:
    db = str(tmp_path / "argus.db")
    exp1 = _exporter(db)
    exp1.export(_snap(power_watts=100.0, offset_seconds=0))
    exp1.export(_snap(power_watts=100.0, offset_seconds=3600))  # 100 Wh

    exp2 = _exporter(db)
    exp2.export(_snap(power_watts=100.0, offset_seconds=3600))
    exp2.export(_snap(power_watts=100.0, offset_seconds=7200))  # +100 Wh

    totals = exp2.get_totals()
    assert totals[0]["energy_wh"] == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# Multi-device
# ---------------------------------------------------------------------------

def test_multiple_devices_tracked_independently(tmp_path: Path) -> None:
    db = str(tmp_path / "argus.db")
    exporter = _exporter(db)
    exporter.export(_snap(device_id="dev-a", power_watts=200.0, offset_seconds=0))
    exporter.export(_snap(device_id="dev-a", power_watts=200.0, offset_seconds=3600))
    exporter.export(_snap(device_id="dev-b", power_watts=100.0, offset_seconds=0))
    exporter.export(_snap(device_id="dev-b", power_watts=100.0, offset_seconds=3600))
    totals = {t["device_id"]: t["energy_wh"] for t in exporter.get_totals()}
    assert totals["dev-a"] == pytest.approx(200.0)
    assert totals["dev-b"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

def test_cost_estimation_when_rate_set(tmp_path: Path) -> None:
    db = str(tmp_path / "argus.db")
    # Rate: $0.12/kWh; 1000 Wh = 1 kWh → cost = $0.12
    exporter = _exporter(db, rate_per_kwh=0.12)
    exporter.export(_snap(power_watts=1000.0, offset_seconds=0))
    exporter.export(_snap(power_watts=1000.0, offset_seconds=3600))
    totals = exporter.get_totals()
    assert "estimated_cost" in totals[0]
    assert totals[0]["estimated_cost"] == pytest.approx(0.12)


def test_no_cost_field_when_rate_is_zero(tmp_path: Path) -> None:
    db = str(tmp_path / "argus.db")
    exporter = _exporter(db, rate_per_kwh=0.0)
    exporter.export(_snap(power_watts=100.0, offset_seconds=0))
    exporter.export(_snap(power_watts=100.0, offset_seconds=3600))
    totals = exporter.get_totals()
    assert "estimated_cost" not in totals[0]


# ---------------------------------------------------------------------------
# kwh conversion in get_totals
# ---------------------------------------------------------------------------

def test_get_totals_includes_energy_kwh(tmp_path: Path) -> None:
    db = str(tmp_path / "argus.db")
    exporter = _exporter(db)
    exporter.export(_snap(power_watts=1000.0, offset_seconds=0))
    exporter.export(_snap(power_watts=1000.0, offset_seconds=3600))
    totals = exporter.get_totals()
    assert totals[0]["energy_kwh"] == pytest.approx(1.0)
