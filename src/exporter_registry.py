"""Registry mapping exporter names to factory callables."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from src import config
from src.exporters.csv_exporter import CSVExporter
from src.exporters.energy_accumulator import EnergyAccumulatorExporter
from src.exporters.prometheus_exporter import PrometheusExporter
from src.exporters.sqlite_exporter import SQLiteExporter

if TYPE_CHECKING:
    from src.exporters.base_exporter import BaseExporter

_LOG = logging.getLogger(__name__)


def _build_influxdb() -> "BaseExporter | None":
    if not config.INFLUXDB_URL or not config.INFLUXDB_TOKEN:
        _LOG.warning("InfluxDB exporter requested but INFLUXDB_URL/INFLUXDB_TOKEN not set.")
        return None
    from src.exporters.influxdb_exporter import InfluxDBExporter
    return InfluxDBExporter(
        url=config.INFLUXDB_URL,
        token=config.INFLUXDB_TOKEN,
        org=config.INFLUXDB_ORG,
        bucket=config.INFLUXDB_BUCKET,
    )


def _build_loki() -> "BaseExporter | None":
    if not config.LOKI_URL:
        _LOG.warning("Loki exporter requested but LOKI_URL not set.")
        return None
    from src.exporters.loki_exporter import LokiExporter
    return LokiExporter(
        url=config.LOKI_URL,
        job_label=config.LOKI_JOB_LABEL,
        timeout_seconds=config.LOKI_TIMEOUT_SECONDS,
    )


EXPORTER_REGISTRY: dict[str, Callable[[], "BaseExporter | None"]] = {
    "sqlite": lambda: SQLiteExporter(
        db_path=config.SQLITE_PATH,
        retention_days=config.SQLITE_RETENTION_DAYS,
        max_rows=config.SQLITE_MAX_ROWS,
    ),
    "prometheus": lambda: PrometheusExporter(
        port=config.PROMETHEUS_PORT,
        disable_labels=config.PROMETHEUS_DISABLE_LABELS,
    ),
    "influxdb": _build_influxdb,
    "loki": _build_loki,
    "csv": lambda: CSVExporter(
        path=config.CSV_PATH,
        max_size_mb=config.CSV_MAX_SIZE_MB,
        retention_days=config.CSV_RETENTION_DAYS,
    ),
    "energy": lambda: EnergyAccumulatorExporter(
        db_path=config.SQLITE_PATH,
        rate_per_kwh=config.ENERGY_RATE_PER_KWH,
    ),
}
