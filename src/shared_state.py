"""Thread-safe shared state for cross-layer access between the scheduler and API."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.services.alert_manager import AlertManager

_lock = threading.Lock()
_alert_manager: Any = None
_last_diagnostics: dict[str, Any] = {}


def set_alert_manager(manager: "AlertManager") -> None:
    global _alert_manager
    with _lock:
        _alert_manager = manager


def get_alert_manager() -> "AlertManager | None":
    with _lock:
        return _alert_manager


def set_last_diagnostics(diagnostics: dict[str, Any]) -> None:
    global _last_diagnostics
    with _lock:
        _last_diagnostics = diagnostics


def get_last_diagnostics() -> dict[str, Any]:
    with _lock:
        return dict(_last_diagnostics)
