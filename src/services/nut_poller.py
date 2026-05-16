"""NUT poller — collects UPS telemetry via the NUT (Network UPS Tools) protocol."""
from __future__ import annotations

import logging
import socket
from datetime import datetime, timezone

from src.constants import DeviceType
from src.models.power_snapshot import PowerSnapshot

_LOG = logging.getLogger(__name__)

# NUT variable → PowerSnapshot field mapping
_NUT_FIELD_MAP: dict[str, str] = {
    "ups.load": "load_percent",
    "ups.realpower": "power_watts",
    "input.voltage": "input_voltage",
    "output.voltage": "output_voltage",
    "battery.charge": "battery_percent",
    "battery.runtime": "runtime_seconds",
    "input.frequency": "frequency_hz",
    "ups.temperature": "temperature_c",
    "ups.status": "ups_status",
}


class NUTPoller:
    """Polls a single UPS device via NUT's simple text protocol."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3493,
        username: str = "",
        password: str = "",
        ups_name: str = "ups",
        timeout: int = 10,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._ups_name = ups_name
        self._timeout = timeout

    def poll(self) -> PowerSnapshot:
        """Connect to NUT, retrieve all variables, and return a PowerSnapshot."""
        raw = self._fetch_vars()
        return self._build_snapshot(raw)

    def _fetch_vars(self) -> dict[str, str]:
        """Open a socket to NUT and retrieve all UPS variables."""
        with socket.create_connection((self._host, self._port), timeout=self._timeout) as sock:
            fh = sock.makefile("rw", buffering=1, encoding="utf-8")

            if self._username:
                fh.write(f"USERNAME {self._username}\n")
                fh.flush()
                resp = fh.readline().strip()
                if not resp.startswith("OK"):
                    raise RuntimeError(f"NUT authentication (username) rejected: {resp}")

            if self._password:
                fh.write(f"PASSWORD {self._password}\n")
                fh.flush()
                resp = fh.readline().strip()
                if not resp.startswith("OK"):
                    raise RuntimeError(f"NUT authentication (password) rejected: {resp}")

            fh.write(f"LIST VAR {self._ups_name}\n")
            fh.flush()

            variables: dict[str, str] = {}
            for line in fh:
                line = line.strip()
                if line == f"END LIST VAR {self._ups_name}":
                    break
                if line.startswith(f"VAR {self._ups_name} "):
                    # Format: VAR <ups> <var> "<value>"
                    parts = line.split(" ", 3)
                    if len(parts) == 4:
                        key = parts[2]
                        value = parts[3].strip('"')
                        variables[key] = value

            fh.write("LOGOUT\n")
            fh.flush()
            return variables

    def _build_snapshot(self, raw: dict[str, str]) -> PowerSnapshot:
        kwargs: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc),
            "device_id": f"nut:{self._ups_name}@{self._host}",
            "device_type": DeviceType.UPS,
        }
        for nut_key, field in _NUT_FIELD_MAP.items():
            value = raw.get(nut_key)
            if value is None:
                continue
            if field == "ups_status":
                kwargs[field] = value
            else:
                try:
                    kwargs[field] = float(value)
                except ValueError:
                    _LOG.warning("Could not parse NUT var %s=%r as float.", nut_key, value)

        # Derive power_watts from load_percent + nominal power if direct reading unavailable
        if kwargs.get("power_watts") is None:
            nominal_raw = raw.get("ups.realpower.nominal") or raw.get("ups.power.nominal")
            if nominal_raw and kwargs.get("load_percent") is not None:
                try:
                    nominal = float(nominal_raw)
                    kwargs["power_watts"] = nominal * (kwargs["load_percent"] / 100.0)  # type: ignore[operator]
                except ValueError:
                    pass

        return PowerSnapshot(**kwargs)  # type: ignore[arg-type]
