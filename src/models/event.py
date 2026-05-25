"""PowerEvent — structured state-transition event emitted by the EventProcessor."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PowerEvent:
    """A structured event emitted when a device state transition is detected."""

    timestamp: datetime
    device_id: str
    event_type: str  # EventType value
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware.")
        if not self.device_id or not self.device_id.strip():
            raise ValueError("device_id must not be empty.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "device_id": self.device_id,
            "event_type": self.event_type,
            "metadata": self.metadata,
        }
