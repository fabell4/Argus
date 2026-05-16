"""Device — entry in the Argus device registry."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Device:
    """A monitored device registered in Argus."""

    id: str
    name: str
    type: str      # DeviceType value
    poller: str    # PollerType value
    host: str
    port: int
    enabled: bool = True
    connection_config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "poller": self.poller,
            "host": self.host,
            "port": self.port,
            "enabled": self.enabled,
            "connection_config": self.connection_config,
        }
