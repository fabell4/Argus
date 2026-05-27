"""Persistent runtime configuration stored in data/runtime_config.json.

Changes made through the UI/API are written here so they survive process restarts.
Both the scheduler process and the API process read/write this file.
Atomic writes (write-to-temp then rename) prevent partial reads.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Any

from src import config
from src.constants import ExporterType

_LOG = logging.getLogger(__name__)
_CONFIG_PATH = os.path.join("data", "runtime_config.json")
_RUN_TRIGGER = os.path.join("data", ".run_trigger")
_RUNNING_SENTINEL = os.path.join("data", ".running")

_DEFAULTS: dict[str, Any] = {
    "poll_interval_minutes": config.POLL_INTERVAL_MINUTES,
    "enabled_exporters": config.ENABLED_EXPORTERS,
    "scanning_disabled": False,
    "scheduler_paused": False,
    "next_poll_at": None,
    "last_poll_at": None,
    "alert_config": {},
    # NUT connection
    "nut_host": config.NUT_HOST,
    "nut_port": config.NUT_PORT,
    "nut_username": config.NUT_USERNAME,
    "nut_password": config.NUT_PASSWORD,
    "nut_ups_name": config.NUT_UPS_NAME,
    "nut_auto_discover": config.NUT_AUTO_DISCOVER,
    # Event thresholds
    "device_offline_missed_polls": config.DEVICE_OFFLINE_MISSED_POLLS,
    "shutdown_battery_floor_pct": config.SHUTDOWN_BATTERY_FLOOR_PCT,
    "threshold_load_percent": config.THRESHOLD_LOAD_PERCENT,
    "threshold_temp_celsius": config.THRESHOLD_TEMP_CELSIUS,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_raw() -> dict[str, Any]:
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as fh:
            data: dict[str, Any] = json.load(fh)
            return data
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        _LOG.warning("runtime_config.json is corrupt; resetting to defaults.")
        return {}


def _save_raw(data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        dir=os.path.dirname(_CONFIG_PATH),
        delete=False,
        suffix=".tmp",
        encoding="utf-8",
    ) as tmp:
        json.dump(data, tmp, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, _CONFIG_PATH)


def load() -> dict[str, Any]:
    """Load config from disk, apply defaults, and sanitize values."""
    data = _DEFAULTS.copy()
    data.update(_load_raw())
    _sanitize(data)
    _apply_env_overrides(data)
    return data


def _sanitize(data: dict[str, Any]) -> None:
    """Coerce and clamp values loaded from disk to valid types and ranges.

    Prevents malformed data in runtime_config.json from propagating into the
    application when the file is manually edited or written by an older version.
    """
    # poll_interval_minutes: must be an int in [1, 10080]
    try:
        minutes = int(data["poll_interval_minutes"])
        data["poll_interval_minutes"] = max(1, min(10080, minutes))
    except (TypeError, ValueError, KeyError):
        data["poll_interval_minutes"] = _DEFAULTS["poll_interval_minutes"]

    # enabled_exporters: must be a list of known exporter strings
    exporters = data.get("enabled_exporters")
    if not isinstance(exporters, list):
        data["enabled_exporters"] = list(_DEFAULTS["enabled_exporters"])
    else:
        data["enabled_exporters"] = [
            e for e in exporters if isinstance(e, str) and e in _VALID_EXPORTERS
        ]

    # boolean flags
    data["scheduler_paused"] = bool(data.get("scheduler_paused", False))
    data["scanning_disabled"] = bool(data.get("scanning_disabled", False))

    # alert_config: must be a dict
    if not isinstance(data.get("alert_config"), dict):
        data["alert_config"] = {}

    # nut_host: non-empty string
    if not isinstance(data.get("nut_host"), str) or not data["nut_host"].strip():
        data["nut_host"] = config.NUT_HOST

    # nut_port: int in [1, 65535]
    try:
        data["nut_port"] = max(
            1, min(65535, int(data.get("nut_port", config.NUT_PORT)))
        )
    except (TypeError, ValueError):
        data["nut_port"] = config.NUT_PORT

    # nut string fields
    for _key, _default in (
        ("nut_username", config.NUT_USERNAME),
        ("nut_password", config.NUT_PASSWORD),
        ("nut_ups_name", config.NUT_UPS_NAME),
    ):
        if not isinstance(data.get(_key), str):
            data[_key] = _default

    # nut_auto_discover: bool
    data["nut_auto_discover"] = bool(
        data.get("nut_auto_discover", config.NUT_AUTO_DISCOVER)
    )

    # device_offline_missed_polls: int >= 1
    try:
        data["device_offline_missed_polls"] = max(
            1,
            int(
                data.get(
                    "device_offline_missed_polls", config.DEVICE_OFFLINE_MISSED_POLLS
                )
            ),
        )
    except (TypeError, ValueError):
        data["device_offline_missed_polls"] = config.DEVICE_OFFLINE_MISSED_POLLS

    # float thresholds
    for _fkey, _fdefault, _lo, _hi in (
        ("shutdown_battery_floor_pct", config.SHUTDOWN_BATTERY_FLOOR_PCT, 0.0, 99.0),
        ("threshold_load_percent", config.THRESHOLD_LOAD_PERCENT, 0.0, 100.0),
        ("threshold_temp_celsius", config.THRESHOLD_TEMP_CELSIUS, 0.0, 200.0),
    ):
        try:
            data[_fkey] = max(_lo, min(_hi, float(data.get(_fkey, _fdefault))))
        except (TypeError, ValueError):
            data[_fkey] = _fdefault


def _apply_env_overrides(data: dict[str, Any]) -> None:
    """Override persisted runtime config values with env vars that were explicitly set.

    An env var is considered explicitly set when its resolved value differs from the
    hard-coded fallback default (the value used when the env var is absent).  This
    ensures that settings in a docker-compose ``env_file`` always take effect, even
    when a stale ``runtime_config.json`` already exists on a persistent volume.

    Settings whose env var matches the fallback default are left unchanged so that
    UI/API changes for those fields continue to persist across restarts.
    """
    _overrides: list[tuple[str, Any, Any]] = [
        ("nut_host",                    config.NUT_HOST,                    "localhost"),
        ("nut_port",                    config.NUT_PORT,                    3493),
        ("nut_username",                config.NUT_USERNAME,                ""),
        ("nut_password",                config.NUT_PASSWORD,                ""),
        ("nut_ups_name",                config.NUT_UPS_NAME,                "ups"),
        ("nut_auto_discover",           config.NUT_AUTO_DISCOVER,           True),
        ("poll_interval_minutes",       config.POLL_INTERVAL_MINUTES,       5),
        ("enabled_exporters",           config.ENABLED_EXPORTERS,           ["sqlite"]),
        ("device_offline_missed_polls", config.DEVICE_OFFLINE_MISSED_POLLS, 3),
        ("shutdown_battery_floor_pct",  config.SHUTDOWN_BATTERY_FLOOR_PCT,  5.0),
        ("threshold_load_percent",      config.THRESHOLD_LOAD_PERCENT,      90.0),
        ("threshold_temp_celsius",      config.THRESHOLD_TEMP_CELSIUS,      50.0),
    ]
    for key, env_val, hard_default in _overrides:
        if env_val != hard_default:
            data[key] = env_val
            _LOG.debug("Env override applied: %s = %r", key, env_val)


def save(data: dict[str, Any]) -> None:
    """Persist *data* to the runtime config file atomically."""
    _save_raw(data)


# ---------------------------------------------------------------------------
# Poll interval
# ---------------------------------------------------------------------------


def get_interval_minutes() -> int:
    """Return the configured poll interval in minutes."""
    return int(load().get("poll_interval_minutes", _DEFAULTS["poll_interval_minutes"]))


def set_interval_minutes(minutes: int) -> None:
    """Validate and persist a new poll interval in minutes."""
    _validate_interval_minutes(minutes)
    data = load()
    data["poll_interval_minutes"] = minutes
    save(data)


# ---------------------------------------------------------------------------
# Enabled exporters
# ---------------------------------------------------------------------------


def get_enabled_exporters() -> list[str]:
    """Return the list of enabled exporter names."""
    return list(load().get("enabled_exporters", _DEFAULTS["enabled_exporters"]))


def set_enabled_exporters(exporters: list[str]) -> None:
    """Validate and persist the list of enabled exporter names."""
    _validate_enabled_exporters(exporters)
    data = load()
    data["enabled_exporters"] = exporters
    save(data)


# ---------------------------------------------------------------------------
# Scheduler paused
# ---------------------------------------------------------------------------


def get_scheduler_paused() -> bool:
    """Return True if the scheduler is currently paused."""
    return bool(load().get("scheduler_paused", False))


def set_scheduler_paused(paused: bool) -> None:
    """Persist the scheduler paused flag."""
    data = load()
    data["scheduler_paused"] = bool(paused)
    save(data)


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------


def get_next_poll_at() -> str | None:
    """Return the ISO-format next-poll timestamp, or None if unset."""
    return load().get("next_poll_at")


def set_next_poll_at(dt: datetime | None) -> None:
    """Persist the next scheduled poll timestamp."""
    data = load()
    data["next_poll_at"] = dt.isoformat() if dt else None
    save(data)


def get_last_poll_at() -> str | None:
    """Return the ISO-format last-poll timestamp, or None if never polled."""
    return load().get("last_poll_at")


def set_last_poll_at(dt: datetime) -> None:
    """Persist the last-poll timestamp."""
    data = load()
    data["last_poll_at"] = dt.isoformat()
    save(data)


# ---------------------------------------------------------------------------
# Manual trigger sentinels
# ---------------------------------------------------------------------------


def trigger_poll() -> None:
    """Signal the scheduler to run an immediate poll."""
    os.makedirs("data", exist_ok=True)
    with open(_RUN_TRIGGER, "w", encoding="utf-8") as f:
        f.write("")


def consume_poll_trigger() -> bool:
    """Return True and remove the trigger file if a manual poll was requested."""
    if os.path.exists(_RUN_TRIGGER):
        try:
            os.remove(_RUN_TRIGGER)
        except FileNotFoundError:
            _LOG.debug(
                "Poll trigger file already removed (TOCTOU race — safe to ignore)."
            )
        return True
    return False


def mark_running() -> None:
    """Create the running sentinel file to signal that the scheduler is active."""
    os.makedirs("data", exist_ok=True)
    with open(_RUNNING_SENTINEL, "w", encoding="utf-8") as f:
        f.write("")


def mark_done() -> None:
    """Remove the running sentinel file."""
    try:
        os.remove(_RUNNING_SENTINEL)
    except FileNotFoundError:
        _LOG.debug("Running sentinel already absent (TOCTOU race — safe to ignore.)")


def is_running() -> bool:
    """Return True if the running sentinel file exists."""
    return os.path.exists(_RUNNING_SENTINEL)


# ---------------------------------------------------------------------------
# Alert config
# ---------------------------------------------------------------------------


def get_alert_config() -> dict[str, Any]:
    """Return a copy of the persisted alert provider configuration."""
    return dict(load().get("alert_config", {}))


def set_alert_config(cfg: dict[str, Any]) -> None:
    """Validate and persist the alert provider configuration."""
    _validate_alert_config(cfg)
    data = load()
    data["alert_config"] = cfg
    save(data)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_interval_minutes(value: int) -> None:
    if not isinstance(value, int) or value < 1 or value > 10080:
        raise ValueError(
            "poll_interval_minutes must be an integer between 1 and 10080."
        )


_VALID_EXPORTERS: frozenset[str] = frozenset(ExporterType)


# ---------------------------------------------------------------------------
# NUT config
# ---------------------------------------------------------------------------


def get_nut_config() -> dict[str, Any]:
    """Return the effective NUT connection config (runtime file → env fallback)."""
    data = load()
    ups_name = str(data.get("nut_ups_name") or config.NUT_UPS_NAME)
    ups_names = [name.strip() for name in ups_name.split(",") if name.strip()]
    return {
        "host": str(data.get("nut_host") or config.NUT_HOST),
        "port": int(data.get("nut_port") or config.NUT_PORT),
        "username": str(data.get("nut_username", config.NUT_USERNAME)),
        "password": str(data.get("nut_password", config.NUT_PASSWORD)),
        "ups_name": ups_name,
        "ups_names": ups_names or [config.NUT_UPS_NAME],
        "auto_discover": bool(data.get("nut_auto_discover", config.NUT_AUTO_DISCOVER)),
    }


# ---------------------------------------------------------------------------
# Event threshold config
# ---------------------------------------------------------------------------


def get_threshold_config() -> dict[str, Any]:
    """Return the effective event threshold config (runtime file → env fallback)."""
    data = load()
    return {
        "device_offline_missed_polls": int(
            data.get("device_offline_missed_polls", config.DEVICE_OFFLINE_MISSED_POLLS)
        ),
        "shutdown_battery_floor_pct": float(
            data.get("shutdown_battery_floor_pct", config.SHUTDOWN_BATTERY_FLOOR_PCT)
        ),
        "threshold_load_percent": float(
            data.get("threshold_load_percent", config.THRESHOLD_LOAD_PERCENT)
        ),
        "threshold_temp_celsius": float(
            data.get("threshold_temp_celsius", config.THRESHOLD_TEMP_CELSIUS)
        ),
    }


def _validate_enabled_exporters(value: list[str]) -> None:
    if not isinstance(value, list) or not all(isinstance(e, str) for e in value):
        raise ValueError("enabled_exporters must be a list of strings.")
    unknown = [e for e in value if e not in _VALID_EXPORTERS]
    if unknown:
        raise ValueError(
            f"Unknown exporter(s): {unknown}. Valid: {sorted(_VALID_EXPORTERS)}"
        )


def _validate_alert_config(value: dict[str, Any]) -> None:
    if not isinstance(value, dict):
        raise ValueError("alert_config must be a dictionary.")
