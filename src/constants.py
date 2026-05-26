"""Application-wide constants and enumerations."""

from __future__ import annotations

from enum import StrEnum


class DeviceType(StrEnum):
    """Device categories used across telemetry and API payloads."""

    UPS = "ups"
    PDU = "pdu"
    SENSOR = "sensor"
    HOST = "host"


class PollerType(StrEnum):
    """Polling backends supported by Argus."""

    NUT = "nut"
    SNMP = "snmp"
    HTTP = "http"


class ExporterType(StrEnum):
    """Snapshot exporter backends available at runtime."""

    SQLITE = "sqlite"
    PROMETHEUS = "prometheus"
    INFLUXDB = "influxdb"
    LOKI = "loki"
    CSV = "csv"
    ENERGY = "energy"


class AlertProviderType(StrEnum):
    """Notification provider types supported by the alert manager."""

    WEBHOOK = "webhook"
    GOTIFY = "gotify"
    NTFY = "ntfy"
    APPRISE = "apprise"


class EventType(StrEnum):
    """Event kinds emitted by event processing and state transitions."""

    ON_BATTERY = "on_battery"
    POWER_RESTORED = "power_restored"
    BATTERY_LOW = "battery_low"
    SHUTDOWN_INITIATED = "shutdown_initiated"
    THRESHOLD_CROSSED = "threshold_crossed"
    DEVICE_OFFLINE = "device_offline"
    DEVICE_ONLINE = "device_online"


class UPSStatus(StrEnum):
    """Canonical UPS status flags normalized from NUT telemetry."""

    ONLINE = "OL"
    ON_BATTERY = "OB"
    LOW_BATTERY = "LB"
    CHARGING = "CHRG"
    DISCHARGING = "DISCHRG"
    BYPASS = "BYPASS"
    UNKNOWN = "UNKNOWN"


class AlertSeverity(StrEnum):
    """Severity levels used to classify alert notifications."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
