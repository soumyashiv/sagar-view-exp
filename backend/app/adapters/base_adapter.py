"""Base adapter interface for all data source adapters."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    """Plugin-style base class for all observation/model data adapters."""

    name: str = "base"
    description: str = ""

    @abstractmethod
    async def list_platforms(self, bbox: dict, **kwargs) -> list[dict]:
        """List available platforms/files in the bounding box."""
        ...

    @abstractmethod
    async def get_profile(self, platform_id: str, **kwargs) -> dict:
        """Return a vertical profile for a platform."""
        ...

    @abstractmethod
    async def get_field(self, variable: str, depth: float, time: Any, **kwargs) -> dict:
        """Return a 2D field for a variable at depth and time."""
        ...

    def capabilities(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "supports_profiles": True,
            "supports_fields": False,
            "supports_timeseries": False,
        }
