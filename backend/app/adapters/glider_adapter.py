"""
Glider data adapter.
Follows the same plugin pattern as ArgoAdapter.
Designed for Seaglider/SLOCUM NetCDF files following IOOS Glider DAC conventions.
"""
from __future__ import annotations
import logging
from app.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class GliderAdapter(BaseAdapter):
    name = "glider"
    description = "Underwater glider observation adapter (IOOS Glider DAC)"

    def __init__(self, dac_url: str = "https://gliders.ioos.us/erddap"):
        self.dac_url = dac_url

    async def list_platforms(self, bbox: dict, **kwargs) -> list[dict]:
        """Query IOOS Glider DAC ERDDAP for gliders in bbox."""
        try:
            import httpx
            params = {
                "minLon": bbox.get("lon_min", 40),
                "maxLon": bbox.get("lon_max", 100),
                "minLat": bbox.get("lat_min", -30),
                "maxLat": bbox.get("lat_max", 30),
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.dac_url}/search/index.json", params=params)
                resp.raise_for_status()
                return resp.json().get("items", [])
        except Exception as exc:
            logger.warning("Glider DAC fetch failed: %s", exc)
            return []

    async def get_profile(self, platform_id: str, **kwargs) -> dict:
        return {}

    async def get_field(self, variable: str, depth: float, time, **kwargs) -> dict:
        return {}
