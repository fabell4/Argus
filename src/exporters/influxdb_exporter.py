"""InfluxDB exporter — forwards snapshots to an InfluxDB v2 bucket."""

from __future__ import annotations

import logging
from datetime import timezone
from typing import Any

from src.exporters.base_exporter import BaseExporter
from src.models.power_snapshot import PowerSnapshot

_LOG = logging.getLogger(__name__)


class InfluxDBExporter(BaseExporter):
    """Writes PowerSnapshot data to InfluxDB v2 using the official client."""

    def __init__(self, url: str, token: str, org: str, bucket: str) -> None:
        self._url = url
        self._token = token
        self._org = org
        self._bucket = bucket
        self._client: Any = self._build_client()

    def _build_client(self) -> Any:
        try:
            from influxdb_client import InfluxDBClient  # type: ignore[import-untyped]
        except ImportError:
            _LOG.warning("influxdb-client not installed; InfluxDB exporter disabled.")
            return None
        client: Any = InfluxDBClient(url=self._url, token=self._token, org=self._org)
        _LOG.info(
            "InfluxDB client initialised (url=%s, bucket=%s).", self._url, self._bucket
        )
        return client

    def export(self, snapshot: PowerSnapshot) -> None:
        if self._client is None:
            return
        try:
            from influxdb_client import Point  # type: ignore[import-untyped]
            from influxdb_client.client.write_api import SYNCHRONOUS  # type: ignore[import-untyped]
        except ImportError:
            _LOG.warning("influxdb-client unavailable; skipping export.")
            return
        point: Any = (
            Point("power_snapshot")
            .tag("device_id", snapshot.device_id)
            .tag("device_type", snapshot.device_type)
            .time(snapshot.timestamp.astimezone(timezone.utc))
        )
        _numeric_fields: dict[str, float | None] = {
            "power_watts": snapshot.power_watts,
            "load_percent": snapshot.load_percent,
            "voltage": snapshot.voltage,
            "battery_percent": snapshot.battery_percent,
            "runtime_seconds": snapshot.runtime_seconds,
            "current_amps": snapshot.current_amps,
            "frequency_hz": snapshot.frequency_hz,
            "temperature_c": snapshot.temperature_c,
            "input_voltage": snapshot.input_voltage,
            "output_voltage": snapshot.output_voltage,
        }
        for field, value in _numeric_fields.items():
            if value is not None:
                point = point.field(field, value)
        write_api = self._client.write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket=self._bucket, org=self._org, record=point)
