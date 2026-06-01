"""Prometheus exporter — exposes Argus device metrics for scraping."""

from __future__ import annotations

import logging

from src.exporters.base_exporter import BaseExporter
from src.models.power_snapshot import PowerSnapshot

_LOG = logging.getLogger(__name__)


class PrometheusExporter(BaseExporter):
    """Exposes PowerSnapshot metrics as Prometheus gauges."""

    def __init__(self, port: int = 9090, disable_labels: bool = False) -> None:
        self._port = port
        self._disable_labels = disable_labels
        self._started = False
        self._gauges: dict[str, object] = {}
        self._init_metrics()

    def _init_metrics(self) -> None:
        try:
            from prometheus_client import Gauge, start_http_server

            labels = [] if self._disable_labels else ["device_id", "device_type"]
            self._gauges = {
                "power_watts": Gauge(
                    "argus_power_watts", "Device power consumption in watts", labels
                ),
                "load_percent": Gauge(
                    "argus_load_percent", "Device load percentage", labels
                ),
                "input_voltage": Gauge(
                    "argus_voltage_volts", "Input voltage in volts", labels
                ),
                "battery_percent": Gauge(
                    "argus_battery_percent", "UPS battery charge percentage", labels
                ),
                "runtime_seconds": Gauge(
                    "argus_runtime_seconds", "UPS estimated runtime in seconds", labels
                ),
                "temperature_c": Gauge(
                    "argus_temperature_celsius", "Device temperature in Celsius", labels
                ),
            }
            if not self._started:
                start_http_server(self._port)
                self._started = True
                _LOG.info("Prometheus metrics server started on port %d.", self._port)
        except ImportError:
            _LOG.warning(
                "prometheus_client not installed; Prometheus exporter disabled."
            )

    def export(self, snapshot: PowerSnapshot) -> None:
        if not self._gauges:
            return
        for metric, gauge in self._gauges.items():
            value = getattr(snapshot, metric, None)
            if value is not None:
                if self._disable_labels:
                    gauge.set(value)  # type: ignore[attr-defined]
                else:
                    gauge.labels(snapshot.device_id, snapshot.device_type).set(value)  # type: ignore[attr-defined]
