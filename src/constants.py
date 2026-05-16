"""Application-wide constants and enumerations."""
from __future__ import annotations

from enum import StrEnum


class DeviceType(StrEnum):
    UPS = "ups"
    PDU = "pdu"
    SENSOR = "sensor"
    HOST = "host"


class PollerType(StrEnum):
    NUT = "nut"
    SNMP = "snmp"
    HTTP = "http"


class ExporterType(StrEnum):
    SQLITE = "sqlite"
    PROMETHEUS = "prometheus"
    INFLUXDB = "influxdb"


class AlertProviderType(StrEnum):
    WEBHOOK = "webhook"
    GOTIFY = "gotify"
    NTFY = "ntfy"
    APPRISE = "apprise"


class EventType(StrEnum):
    ON_BATTERY = "on_battery"
    POWER_RESTORED = "power_restored"
    BATTERY_LOW = "battery_low"
    SHUTDOWN_INITIATED = "shutdown_initiated"
    THRESHOLD_CROSSED = "threshold_crossed"
    DEVICE_OFFLINE = "device_offline"
    DEVICE_ONLINE = "device_online"


class UPSStatus(StrEnum):
    ONLINE = "OL"
    ON_BATTERY = "OB"
    LOW_BATTERY = "LB"
    CHARGING = "CHRG"
    DISCHARGING = "DISCHRG"
    BYPASS = "BYPASS"
    UNKNOWN = "UNKNOWN"
