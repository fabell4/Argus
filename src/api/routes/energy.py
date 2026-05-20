"""GET /api/energy — cumulative energy consumption per device."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src import config
from src.exporters.energy_accumulator import EnergyAccumulatorExporter

router = APIRouter(tags=["energy"])

# Single shared instance so it reads from the same SQLite file the exporter writes.
_accumulator = EnergyAccumulatorExporter(
    db_path=config.SQLITE_PATH,
    rate_per_kwh=config.ENERGY_RATE_PER_KWH,
)


@router.get("/energy")
def get_energy() -> list[dict[str, Any]]:
    """Return cumulative kWh totals for every monitored device."""
    return _accumulator.get_totals()
