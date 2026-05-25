"""Device — entry in the Argus device registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Device:
    """A monitored device registered in Argus."""

    id: str
    name: str
    type: str  # DeviceType value
    poller: str  # PollerType value
    host: str
    port: int
    enabled: bool = True
    connection_config: dict[str, Any] = field(default_factory=dict)
    # UPS model/firmware metadata populated from NUT LIST VAR
    model: str | None = None
    firmware: str | None = None
    serial: str | None = None
    manufacturer: str | None = None
    last_seen: str | None = None  # ISO-8601 UTC timestamp

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
            "model": self.model,
            "firmware": self.firmware,
            "serial": self.serial,
            "manufacturer": self.manufacturer,
            "last_seen": self.last_seen,
        }
