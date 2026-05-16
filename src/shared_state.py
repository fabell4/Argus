"""Thread-safe shared state for cross-layer access between the scheduler and API."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.services.alert_manager import AlertManager


@dataclass
class _SharedState:
    """Container for module-level shared state."""
    alert_manager: Any = None
    last_diagnostics: dict[str, Any] = field(default_factory=dict)


_lock = threading.Lock()
_state = _SharedState()


def set_alert_manager(manager: "AlertManager") -> None:
    with _lock:
        _state.alert_manager = manager


def get_alert_manager() -> "AlertManager | None":
    with _lock:
        manager: "AlertManager | None" = _state.alert_manager
        return manager


def set_last_diagnostics(diagnostics: dict[str, Any]) -> None:
    with _lock:
        _state.last_diagnostics = diagnostics


def get_last_diagnostics() -> dict[str, Any]:
    with _lock:
        return dict(_state.last_diagnostics)
