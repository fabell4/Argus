"""SNMP poller — collects telemetry from PDUs, UPS, and sensors via SNMP."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src import config
from src.models.power_snapshot import PowerSnapshot

_LOG = logging.getLogger(__name__)

# Standard UPS MIB (RFC 1628) OIDs
_UPS_MIB: dict[str, str] = {
    "1.3.6.1.2.1.33.1.3.3.1.3.1": "input_voltage",     # upsInputVoltage
    "1.3.6.1.2.1.33.1.4.4.1.2.1": "output_voltage",    # upsOutputVoltage
    "1.3.6.1.2.1.33.1.4.4.1.5.1": "load_percent",      # upsOutputPercentLoad
    "1.3.6.1.2.1.33.1.2.4.0": "battery_percent",       # upsBatteryCapacity
    "1.3.6.1.2.1.33.1.2.3.0": "runtime_seconds",       # upsEstimatedMinutesRemaining → converted
    "1.3.6.1.2.1.33.1.4.4.1.4.1": "power_watts",       # upsOutputPower
}


class SNMPPoller:
    """Polls a device via SNMP and returns a PowerSnapshot."""

    def __init__(
        self,
        host: str,
        port: int = 161,
        community: str = "public",
        version: str = "2c",
        device_id: str | None = None,
        device_type: str = "pdu",
        oids: dict[str, str] | None = None,
        timeout: int | None = None,
        retries: int | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._community = community
        self._version = version
        self._device_id = device_id or f"snmp:{host}:{port}"
        self._device_type = device_type
        self._oids = oids or _UPS_MIB
        self._timeout = timeout if timeout is not None else config.SNMP_TIMEOUT
        self._retries = retries if retries is not None else config.SNMP_RETRIES

    def poll(self) -> PowerSnapshot:
        raw = self._snmp_get(list(self._oids.keys()))
        return self._build_snapshot(raw)

    def _snmp_get(self, oids: list[str]) -> dict[str, Any]:
        """Perform SNMP GET for each OID; returns {oid: value} dict."""
        try:
            from pysnmp.hlapi import (
                CommunityData,
                ContextData,
                ObjectIdentity,
                ObjectType,
                SnmpEngine,
                UdpTransportTarget,
                getCmd,
            )
        except ImportError:
            _LOG.warning("pysnmp not installed; SNMP polling unavailable.")
            return {}

        results: dict[str, Any] = {}
        engine = SnmpEngine()
        for oid in oids:
            error_indication, error_status, _, var_binds = next(
                getCmd(
                    engine,
                    CommunityData(self._community, mpModel=0 if self._version == "1" else 1),
                    UdpTransportTarget(
                        (self._host, self._port),
                        timeout=self._timeout,
                        retries=self._retries,
                    ),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid)),
                )
            )
            if error_indication:
                _LOG.warning("SNMP error for OID %s: %s", oid, error_indication)
                continue
            if error_status:
                _LOG.warning("SNMP error status for OID %s: %s", oid, error_status)
                continue
            for var_bind in var_binds:
                results[str(var_bind[0])] = var_bind[1].prettyPrint()

        return results

    def _build_snapshot(self, raw: dict[str, Any]) -> PowerSnapshot:
        kwargs: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc),
            "device_id": self._device_id,
            "device_type": self._device_type,
        }
        for oid, field in self._oids.items():
            value = raw.get(oid)
            if value is None:
                continue
            try:
                numeric = float(value)
                # Convert runtime from minutes (UPS MIB) to seconds
                if field == "runtime_seconds":
                    numeric *= 60.0
                kwargs[field] = numeric
            except ValueError:
                _LOG.warning("Could not parse SNMP OID %s=%r as float.", oid, value)

        return PowerSnapshot(**kwargs)
