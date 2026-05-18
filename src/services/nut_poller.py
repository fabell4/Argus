"""NUT poller — collects UPS telemetry via the NUT (Network UPS Tools) protocol."""
from __future__ import annotations

import logging
import socket
from datetime import datetime, timezone
from typing import Any

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
        max_retries: int = 1,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._ups_name = ups_name
        self._timeout = timeout
        self._max_retries = max_retries

    def poll(self) -> PowerSnapshot:
        """Connect to NUT, retrieve all variables, and return a PowerSnapshot.

        Retries up to ``max_retries`` times on transient socket errors.
        Authentication failures and protocol errors (``RuntimeError``) propagate
        immediately and are not retried.
        """
        last_exc: OSError = OSError(
            f"All {self._max_retries + 1} poll attempt(s) for "
            f"{self._ups_name}@{self._host}:{self._port} failed."
        )
        for attempt in range(self._max_retries + 1):
            try:
                raw = self._fetch_vars()
                return self._build_snapshot(raw)
            except OSError as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    _LOG.warning(
                        "NUT poll attempt %d/%d failed (%s); retrying.",
                        attempt + 1,
                        self._max_retries + 1,
                        exc,
                    )
        raise last_exc

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

    @staticmethod
    def _apply_field(
        field: str, nut_key: str, value: str, kwargs: dict[str, Any]
    ) -> None:
        """Parse a single NUT variable and store it in ``kwargs``."""
        if field == "ups_status":
            kwargs[field] = value
            return
        try:
            kwargs[field] = float(value)
        except ValueError:
            _LOG.warning("Could not parse NUT var %s=%r as float.", nut_key, value)

    @staticmethod
    def _derive_power_watts(
        raw: dict[str, str], kwargs: dict[str, Any]
    ) -> None:
        """Derive power_watts from nominal capacity and load_percent when not directly available."""
        if kwargs.get("power_watts") is not None:
            return
        nominal_raw = raw.get("ups.realpower.nominal") or raw.get("ups.power.nominal")
        if not nominal_raw:
            return
        load = kwargs.get("load_percent")
        if load is None:
            return
        try:
            kwargs["power_watts"] = float(nominal_raw) * (float(load) / 100.0)
        except (ValueError, TypeError):
            pass

    def _build_snapshot(self, raw: dict[str, str]) -> PowerSnapshot:
        kwargs: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc),
            "device_id": f"nut:{self._ups_name}@{self._host}",
            "device_type": DeviceType.UPS,
        }
        for nut_key, field in _NUT_FIELD_MAP.items():
            value = raw.get(nut_key)
            if value is not None:
                self._apply_field(field, nut_key, value, kwargs)
        self._derive_power_watts(raw, kwargs)
        return PowerSnapshot(**kwargs)
