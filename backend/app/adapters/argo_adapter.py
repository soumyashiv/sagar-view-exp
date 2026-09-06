"""
Argo float adapter — wraps argopy library.
In demo mode, synthetic profiles are used instead.
"""
from __future__ import annotations
import logging
from app.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class ArgoAdapter(BaseAdapter):
    name = "argo"
    description = "Argo float observation adapter (via argopy / Argovis)"

    async def list_platforms(self, bbox: dict, **kwargs) -> list[dict]:
        """List Argo floats in bbox using argopy."""
        try:
            import argopy  # type: ignore
            fetcher = argopy.DataFetcher(backend="argovis")
            ds = fetcher.region([
                bbox.get("lon_min", 40), bbox.get("lon_max", 100),
                bbox.get("lat_min", -30), bbox.get("lat_max", 30),
                0, 2000,
                kwargs.get("date_start", "2023-01-01"),
                kwargs.get("date_end", "2023-12-31"),
            ]).to_xarray()
            # Convert to list of dicts
            return [{"platform_id": str(wmo)} for wmo in ds["PLATFORM_NUMBER"].values[:50]]
        except Exception as exc:
            logger.warning("argopy fetch failed: %s", exc)
            return []

    async def get_profile(self, platform_id: str, **kwargs) -> dict:
        try:
            import argopy  # type: ignore
            fetcher = argopy.DataFetcher(backend="argovis")
            ds = fetcher.profile(int(platform_id), kwargs.get("cycle", 1)).to_xarray()
            return {"dataset": ds, "platform_id": platform_id}
        except Exception as exc:
            logger.warning("argopy profile fetch failed: %s", exc)
            return {}

    async def get_field(self, variable: str, depth: float, time, **kwargs) -> dict:
        # Argo is point observation, not gridded field
        return {}
