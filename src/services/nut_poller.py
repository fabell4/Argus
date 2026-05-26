"""NUT poller — collects UPS telemetry via the NUT (Network UPS Tools) protocol."""

from __future__ import annotations

import io
import logging
import socket
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar

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

# NUT variables captured as device metadata (not stored in PowerSnapshot)
_NUT_METADATA_KEYS: tuple[str, ...] = (
    "ups.model",
    "ups.firmware",
    "ups.serial",
    "ups.mfr",
)


_T = TypeVar("_T")


class NUTPoller:
    """Polls a single UPS device via NUT's simple text protocol."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3493,
        username: str = "",
        password: str = "",  # nosec B107 — empty default is intentional; NUT auth is optional
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

    def _with_retry(
        self, func: Callable[[], _T], operation: str
    ) -> _T:  # NOSONAR python:S6796 — PEP 695 syntax requires Python 3.12+; CI runner uses 3.11
        """Run *func*, retrying up to ``max_retries`` times on :class:`OSError`."""
        last_exc: OSError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return func()
            except OSError as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    _LOG.warning(
                        "%s attempt %d/%d failed (%s); retrying.",
                        operation,
                        attempt + 1,
                        self._max_retries + 1,
                        exc,
                    )
        if last_exc is None:  # pragma: no cover — loop always executes at least once
            raise RuntimeError(f"{operation} failed with no recorded exception")
        raise last_exc

    def poll(self) -> PowerSnapshot:
        """Connect to NUT, retrieve all variables, and return a PowerSnapshot.

        Retries up to ``max_retries`` times on transient socket errors.
        Authentication failures and protocol errors (``RuntimeError``) propagate
        immediately and are not retried.
        """

        def _do() -> PowerSnapshot:
            raw = self._fetch_vars()
            return self._build_snapshot(raw)

        return self._with_retry(
            _do, f"NUT poll for {self._ups_name}@{self._host}:{self._port}"
        )

    # ------------------------------------------------------------------
    # NUT protocol helpers
    # ------------------------------------------------------------------

    def _authenticate(self, fh: io.TextIOWrapper) -> None:
        """Send USERNAME / PASSWORD to an open NUT file handle if credentials are set."""
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

    def _fetch_vars(self) -> dict[str, str]:
        """Open a socket to NUT and retrieve all UPS variables."""
        with socket.create_connection(
            (self._host, self._port), timeout=self._timeout
        ) as sock:
            fh = sock.makefile("rw", buffering=1, encoding="utf-8")
            self._authenticate(fh)

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

    def _fetch_ups_list(self) -> list[str]:
        """Query LIST UPS and return all UPS names served by the NUT daemon."""
        with socket.create_connection(
            (self._host, self._port), timeout=self._timeout
        ) as sock:
            fh = sock.makefile("rw", buffering=1, encoding="utf-8")
            self._authenticate(fh)

            fh.write("LIST UPS\n")
            fh.flush()

            names: list[str] = []
            for line in fh:
                line = line.strip()
                if line == "END LIST UPS":
                    break
                if line.startswith("UPS "):
                    # Format: UPS <name> "<description>"
                    parts = line.split(" ", 2)
                    if len(parts) >= 2:
                        names.append(parts[1])

            fh.write("LOGOUT\n")
            fh.flush()
            return names

    # ------------------------------------------------------------------
    # Public poll API
    # ------------------------------------------------------------------

    def list_ups(self) -> list[str]:
        """Return all UPS names served by this NUT daemon.

        Retries up to ``max_retries`` times on transient socket errors.
        """
        return self._with_retry(
            self._fetch_ups_list,
            f"LIST UPS for {self._host}:{self._port}",
        )

    def poll_with_metadata(
        self,
    ) -> tuple[PowerSnapshot, dict[str, str]]:
        """Like :meth:`poll` but also returns UPS metadata (model, firmware, serial, mfr)."""

        def _do() -> tuple[PowerSnapshot, dict[str, str]]:
            raw = self._fetch_vars()
            snapshot = self._build_snapshot(raw)
            metadata = {k: raw[k] for k in _NUT_METADATA_KEYS if k in raw}
            return snapshot, metadata

        return self._with_retry(
            _do, f"NUT poll for {self._ups_name}@{self._host}:{self._port}"
        )

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
    def _derive_power_watts(raw: dict[str, str], kwargs: dict[str, Any]) -> None:
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
        except (ValueError, TypeError) as exc:
            _LOG.debug(
                "Could not derive power_watts from NUT vars (%s); skipping.", exc
            )

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
