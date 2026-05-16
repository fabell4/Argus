"""Shared type aliases."""
from __future__ import annotations

from typing import Any

JsonDict = dict[str, Any]       # Generic JSON-serialisable dict
DeviceConfig = dict[str, Any]   # Raw device connection configuration
AlertConfig = dict[str, Any]    # Alert configuration dict
