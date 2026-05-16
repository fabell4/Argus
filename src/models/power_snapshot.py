"""PowerSnapshot — the canonical telemetry unit for Argus."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class PowerSnapshot:
    """A single telemetry snapshot collected from a monitored device."""

    timestamp: datetime
    device_id: str
    device_type: str  # DeviceType value

    # Power metrics (optional — not all devices expose all fields)
    power_watts: float | None = None
    load_percent: float | None = None
    voltage: float | None = None
    battery_percent: float | None = None
    runtime_seconds: float | None = None
    current_amps: float | None = None
    frequency_hz: float | None = None
    temperature_c: float | None = None

    # UPS-specific
    ups_status: str | None = None
    input_voltage: float | None = None
    output_voltage: float | None = None

    # PDU-specific
    outlet_count: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be a datetime instance.")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware.")
        if not self.device_id or not self.device_id.strip():
            raise ValueError("device_id must not be empty.")
        if self.load_percent is not None and not (0.0 <= self.load_percent <= 100.0):
            raise ValueError("load_percent must be between 0 and 100.")
        if self.battery_percent is not None and not (0.0 <= self.battery_percent <= 100.0):
            raise ValueError("battery_percent must be between 0 and 100.")
        if self.power_watts is not None and self.power_watts < 0:
            raise ValueError("power_watts must be non-negative.")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "device_id": self.device_id,
            "device_type": self.device_type,
            "power_watts": self.power_watts,
            "load_percent": self.load_percent,
            "voltage": self.voltage,
            "battery_percent": self.battery_percent,
            "runtime_seconds": self.runtime_seconds,
            "current_amps": self.current_amps,
            "frequency_hz": self.frequency_hz,
            "temperature_c": self.temperature_c,
            "ups_status": self.ups_status,
            "input_voltage": self.input_voltage,
            "output_voltage": self.output_voltage,
            "outlet_count": self.outlet_count,
        }
