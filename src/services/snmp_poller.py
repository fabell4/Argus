"""SNMP poller — collects telemetry from PDUs, UPS, and sensors via SNMP."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src import config
from src.models.power_snapshot import PowerSnapshot

_LOG = logging.getLogger(__name__)

# Standard UPS MIB (RFC 1628) OIDs
_UPS_MIB: dict[str, str] = {
    "1.3.6.1.2.1.33.1.3.3.1.3.1": "input_voltage",  # upsInputVoltage
    "1.3.6.1.2.1.33.1.4.4.1.2.1": "output_voltage",  # upsOutputVoltage
    "1.3.6.1.2.1.33.1.4.4.1.5.1": "load_percent",  # upsOutputPercentLoad
    "1.3.6.1.2.1.33.1.2.4.0": "battery_percent",  # upsBatteryCapacity
    "1.3.6.1.2.1.33.1.2.3.0": "runtime_seconds",  # upsEstimatedMinutesRemaining → converted
    "1.3.6.1.2.1.33.1.4.4.1.4.1": "power_watts",  # upsOutputPower
}


@dataclass
class SNMPv3Config:
    """SNMPv3 authPriv credentials.  Pass to ``SNMPPoller`` via ``v3_config``."""

    username: str
    auth_protocol: str = "MD5"
    auth_key: str = ""
    priv_protocol: str = "DES"
    priv_key: str = ""


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
        max_retries: int = 1,
        v3_config: SNMPv3Config | None = None,
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
        self._max_retries = max_retries
        _v3 = v3_config or SNMPv3Config(username="")
        self._v3_username = _v3.username
        self._v3_auth_protocol = _v3.auth_protocol.upper()
        self._v3_auth_key = _v3.auth_key
        self._v3_priv_protocol = _v3.priv_protocol.upper()
        self._v3_priv_key = _v3.priv_key

    def poll(self) -> PowerSnapshot:
        """Perform SNMP GET for all OIDs and return a PowerSnapshot.

        Retries once on transient OS-level errors. SNMP protocol-level retries
        are handled internally by pysnmp via the ``retries`` parameter.
        """
        last_exc: OSError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                raw = self._snmp_get(list(self._oids.keys()))
                return self._build_snapshot(raw)
            except OSError as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    _LOG.warning(
                        "SNMP poll attempt %d/%d failed (%s); retrying.",
                        attempt + 1,
                        self._max_retries + 1,
                        exc,
                    )
        if last_exc is not None:
            raise last_exc
        return self._build_snapshot({})  # pragma: no cover

    def _snmp_get(self, oids: list[str]) -> dict[str, Any]:
        """Perform SNMP GET for each OID; returns {oid: value} dict."""
        try:
            from pysnmp.hlapi import (  # type: ignore[import-untyped]
                CommunityData,
                ContextData,
                ObjectIdentity,
                ObjectType,
                SnmpEngine,
                UdpTransportTarget,
                UsmUserData,
                getCmd,
            )
            from pysnmp.proto.rfc1905 import noSuchObject  # type: ignore[import-untyped]
        except ImportError:
            _LOG.warning("pysnmp not installed; SNMP polling unavailable.")
            return {}

        # Build auth data — SNMPv3 when username is set, else community string
        if self._v3_username:
            auth_data = self._build_v3_auth(UsmUserData)
        else:
            mp_model = 0 if self._version == "1" else 1
            auth_data = CommunityData(self._community, mpModel=mp_model)

        results: dict[str, Any] = {}
        engine = SnmpEngine()
        transport = UdpTransportTarget(
            (self._host, self._port),
            timeout=self._timeout,
            retries=self._retries,
        )
        for oid in oids:
            error_indication, error_status, _, var_binds = next(
                getCmd(
                    engine,
                    auth_data,
                    transport,
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
                value = var_bind[1]
                if isinstance(value, noSuchObject.__class__):
                    continue
                results[str(var_bind[0])] = value.prettyPrint()

        return results

    def _build_v3_auth(self, usm_cls: type) -> object:  # type: ignore[type-arg]
        """Construct a UsmUserData instance for authPriv mode."""
        try:
            from pysnmp.hlapi import (  # type: ignore[import-untyped]
                usmAesCfb128Protocol,
                usmDESPrivProtocol,
                usmHMAC128SHA224AuthProtocol,
                usmHMAC192SHA256AuthProtocol,
                usmHMACMD5AuthProtocol,
                usmHMACSHAAuthProtocol,
                usmNoAuthProtocol,
                usmNoPrivProtocol,
            )
        except ImportError:
            _LOG.warning("pysnmp SNMPv3 protocol constants unavailable; falling back.")
            return usm_cls(self._v3_username)

        _auth_map = {
            "MD5": usmHMACMD5AuthProtocol,
            "SHA": usmHMACSHAAuthProtocol,
            "SHA224": usmHMAC128SHA224AuthProtocol,
            "SHA256": usmHMAC192SHA256AuthProtocol,
            "NONE": usmNoAuthProtocol,
        }
        _priv_map = {
            "DES": usmDESPrivProtocol,
            "AES": usmAesCfb128Protocol,
            "NONE": usmNoPrivProtocol,
        }

        auth_proto = _auth_map.get(self._v3_auth_protocol, usmHMACMD5AuthProtocol)
        priv_proto = _priv_map.get(self._v3_priv_protocol, usmDESPrivProtocol)

        return usm_cls(
            self._v3_username,
            authKey=self._v3_auth_key or None,
            privKey=self._v3_priv_key or None,
            authProtocol=auth_proto,
            privProtocol=priv_proto,
        )

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
