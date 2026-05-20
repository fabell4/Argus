"""Central configuration for Argus, loaded from environment variables / .env file."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _get_str(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def _get_int(key: str, default: int) -> int:
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _get_csv_list(key: str, default: list[str] | None = None) -> list[str]:
    raw = os.getenv(key, "")
    if not raw.strip():
        return default or []
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Application ---
APP_ENV: str = _get_str("APP_ENV", "production")
LOG_LEVEL: str = _get_str("LOG_LEVEL", "INFO").upper()
TZ: str = _get_str("TZ", "UTC")

# --- Polling ---
POLL_INTERVAL_MINUTES: int = _get_int("POLL_INTERVAL_MINUTES", 5)
POLL_ON_STARTUP: bool = _get_bool("POLL_ON_STARTUP", True)

# --- NUT ---
NUT_HOST: str = _get_str("NUT_HOST", "localhost")
NUT_PORT: int = _get_int("NUT_PORT", 3493)
NUT_USERNAME: str = _get_str("NUT_USERNAME", "")
NUT_PASSWORD: str = _get_str("NUT_PASSWORD", "")
NUT_UPS_NAME: str = _get_str("NUT_UPS_NAME", "ups")
NUT_AUTO_DISCOVER: bool = _get_bool("NUT_AUTO_DISCOVER", True)

# --- SNMP ---
SNMP_COMMUNITY: str = _get_str("SNMP_COMMUNITY", "public")
SNMP_VERSION: str = _get_str("SNMP_VERSION", "2c")
SNMP_TIMEOUT: int = _get_int("SNMP_TIMEOUT", 5)
SNMP_RETRIES: int = _get_int("SNMP_RETRIES", 2)

# --- SNMPv3 ---
SNMP_V3_USERNAME: str = _get_str("SNMP_V3_USERNAME", "")
SNMP_V3_AUTH_PROTOCOL: str = _get_str("SNMP_V3_AUTH_PROTOCOL", "MD5")
SNMP_V3_AUTH_KEY: str = _get_str("SNMP_V3_AUTH_KEY", "")
SNMP_V3_PRIV_PROTOCOL: str = _get_str("SNMP_V3_PRIV_PROTOCOL", "DES")
SNMP_V3_PRIV_KEY: str = _get_str("SNMP_V3_PRIV_KEY", "")

# --- Exporters ---
ENABLED_EXPORTERS: list[str] = _get_csv_list("ENABLED_EXPORTERS", ["sqlite"])

# --- SQLite ---
SQLITE_PATH: str = _get_str("SQLITE_PATH", "data/argus.db")
SQLITE_RETENTION_DAYS: int = _get_int("SQLITE_RETENTION_DAYS", 90)
SQLITE_MAX_ROWS: int = _get_int("SQLITE_MAX_ROWS", 100_000)

# --- Prometheus ---
PROMETHEUS_ENABLED: bool = _get_bool("PROMETHEUS_ENABLED", False)
PROMETHEUS_PORT: int = _get_int("PROMETHEUS_PORT", 9090)
PROMETHEUS_DISABLE_LABELS: bool = _get_bool("PROMETHEUS_DISABLE_LABELS", False)

# --- InfluxDB ---
INFLUXDB_ENABLED: bool = _get_bool("INFLUXDB_ENABLED", False)
INFLUXDB_URL: str = _get_str("INFLUXDB_URL", "")
INFLUXDB_TOKEN: str = _get_str("INFLUXDB_TOKEN", "")
INFLUXDB_ORG: str = _get_str("INFLUXDB_ORG", "")
INFLUXDB_BUCKET: str = _get_str("INFLUXDB_BUCKET", "argus")

# --- API ---
API_HOST: str = _get_str("API_HOST", "0.0.0.0")
API_PORT: int = _get_int("API_PORT", 8000)
API_KEY: str = _get_str("API_KEY", "")
ALLOWED_ORIGINS: list[str] = _get_csv_list(
    "ALLOWED_ORIGINS", ["http://localhost:3000", "http://localhost:5173"]
)
RATE_LIMIT_PER_MINUTE: int = _get_int("RATE_LIMIT_PER_MINUTE", 60)

# --- Alerting ---
ALERT_FAILURE_THRESHOLD: int = _get_int("ALERT_FAILURE_THRESHOLD", 3)
ALERT_COOLDOWN_SECONDS: int = _get_int("ALERT_COOLDOWN_SECONDS", 3600)
WEBHOOK_URL: str = _get_str("WEBHOOK_URL", "")
GOTIFY_URL: str = _get_str("GOTIFY_URL", "")
GOTIFY_TOKEN: str = _get_str("GOTIFY_TOKEN", "")
NTFY_URL: str = _get_str("NTFY_URL", "")
NTFY_TOPIC: str = _get_str("NTFY_TOPIC", "")
APPRISE_URL: str = _get_str("APPRISE_URL", "")

# --- Loki ---
LOKI_URL: str = _get_str("LOKI_URL", "")
LOKI_JOB_LABEL: str = _get_str("LOKI_JOB_LABEL", "argus_power")
LOKI_TIMEOUT_SECONDS: float = float(_get_int("LOKI_TIMEOUT_SECONDS", 5))

# --- CSV exporter ---
CSV_PATH: str = _get_str("CSV_PATH", "data/argus.csv")
CSV_MAX_SIZE_MB: float = float(_get_int("CSV_MAX_SIZE_MB", 10))
CSV_RETENTION_DAYS: int = _get_int("CSV_RETENTION_DAYS", 30)

# --- Energy accumulation ---
ENERGY_RATE_PER_KWH: float = float(os.getenv("ENERGY_RATE_PER_KWH", "0"))

# --- Event thresholds ---
DEVICE_OFFLINE_MISSED_POLLS: int = _get_int("DEVICE_OFFLINE_MISSED_POLLS", 3)
SHUTDOWN_BATTERY_FLOOR_PCT: float = float(os.getenv("SHUTDOWN_BATTERY_FLOOR_PCT", "5"))
THRESHOLD_LOAD_PERCENT: float = float(os.getenv("THRESHOLD_LOAD_PERCENT", "90"))
THRESHOLD_TEMP_CELSIUS: float = float(os.getenv("THRESHOLD_TEMP_CELSIUS", "50"))

# --- Health ---
HEALTH_PORT: int = _get_int("HEALTH_PORT", 9100)


def validate() -> None:
    """Raise ValueError for fatal misconfigurations."""
    if API_KEY and len(API_KEY) < 32:
        raise ValueError("API_KEY must be at least 32 characters long.")
    if POLL_INTERVAL_MINUTES < 1 or POLL_INTERVAL_MINUTES > 10080:
        raise ValueError("POLL_INTERVAL_MINUTES must be between 1 and 10080.")
