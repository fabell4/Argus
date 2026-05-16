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
        "w", dir=os.path.dirname(_CONFIG_PATH), delete=False, suffix=".tmp", encoding="utf-8"
    ) as tmp:
        json.dump(data, tmp, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, _CONFIG_PATH)


def load() -> dict[str, Any]:
    data = _DEFAULTS.copy()
    data.update(_load_raw())
    return data


def save(data: dict[str, Any]) -> None:
    _save_raw(data)


# ---------------------------------------------------------------------------
# Poll interval
# ---------------------------------------------------------------------------

def get_interval_minutes() -> int:
    return int(load().get("poll_interval_minutes", _DEFAULTS["poll_interval_minutes"]))


def set_interval_minutes(minutes: int) -> None:
    _validate_interval_minutes(minutes)
    data = load()
    data["poll_interval_minutes"] = minutes
    save(data)


# ---------------------------------------------------------------------------
# Enabled exporters
# ---------------------------------------------------------------------------

def get_enabled_exporters() -> list[str]:
    return list(load().get("enabled_exporters", _DEFAULTS["enabled_exporters"]))


def set_enabled_exporters(exporters: list[str]) -> None:
    _validate_enabled_exporters(exporters)
    data = load()
    data["enabled_exporters"] = exporters
    save(data)


# ---------------------------------------------------------------------------
# Scheduler paused
# ---------------------------------------------------------------------------

def get_scheduler_paused() -> bool:
    return bool(load().get("scheduler_paused", False))


def set_scheduler_paused(paused: bool) -> None:
    data = load()
    data["scheduler_paused"] = bool(paused)
    save(data)


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------

def get_next_poll_at() -> str | None:
    return load().get("next_poll_at")


def set_next_poll_at(dt: datetime | None) -> None:
    data = load()
    data["next_poll_at"] = dt.isoformat() if dt else None
    save(data)


def get_last_poll_at() -> str | None:
    return load().get("last_poll_at")


def set_last_poll_at(dt: datetime) -> None:
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
            pass
        return True
    return False


def mark_running() -> None:
    os.makedirs("data", exist_ok=True)
    with open(_RUNNING_SENTINEL, "w", encoding="utf-8") as f:
        f.write("")


def mark_done() -> None:
    try:
        os.remove(_RUNNING_SENTINEL)
    except FileNotFoundError:
        pass


def is_running() -> bool:
    return os.path.exists(_RUNNING_SENTINEL)


# ---------------------------------------------------------------------------
# Alert config
# ---------------------------------------------------------------------------

def get_alert_config() -> dict[str, Any]:
    return dict(load().get("alert_config", {}))


def set_alert_config(cfg: dict[str, Any]) -> None:
    _validate_alert_config(cfg)
    data = load()
    data["alert_config"] = cfg
    save(data)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_interval_minutes(value: int) -> None:
    if not isinstance(value, int) or value < 1 or value > 10080:
        raise ValueError("poll_interval_minutes must be an integer between 1 and 10080.")


def _validate_enabled_exporters(value: list[str]) -> None:
    if not isinstance(value, list) or not all(isinstance(e, str) for e in value):
        raise ValueError("enabled_exporters must be a list of strings.")


def _validate_alert_config(value: dict[str, Any]) -> None:
    if not isinstance(value, dict):
        raise ValueError("alert_config must be a dictionary.")
