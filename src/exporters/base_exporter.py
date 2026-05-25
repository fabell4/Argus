"""Abstract base class for all Argus exporters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.models.power_snapshot import PowerSnapshot


class BaseExporter(ABC):
    """All exporters must implement this interface."""

    @abstractmethod
    def export(self, snapshot: PowerSnapshot) -> None:
        """Persist or forward a single PowerSnapshot."""
