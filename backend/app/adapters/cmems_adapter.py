"""
CMEMS (Copernicus Marine) adapter.
Downloads Indian Ocean subsets via copernicusmarine toolbox.
Requires: pip install copernicusmarine + CMEMS credentials.
In demo mode, this adapter is not invoked.
"""
from __future__ import annotations
import logging
from app.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class CMEMSAdapter(BaseAdapter):
    name = "cmems"
    description = "Copernicus Marine Service — NEMO/IBI/GLO12 models"

    # Known Indian Ocean product IDs
    PRODUCTS = {
        "global_physics_analysisforecast": "cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
        "global_physics_reanalysis": "cmems_mod_glo_phy_my_0.083_P1D-m",
    }

    def __init__(self, username: str | None = None, password: str | None = None):
        self.username = username
        self.password = password

    async def list_platforms(self, bbox: dict, **kwargs) -> list[dict]:
        # CMEMS provides model fields, not discrete observation platforms
        return []

    async def get_profile(self, platform_id: str, **kwargs) -> dict:
        return {}

    async def get_field(self, variable: str, depth: float, time, **kwargs) -> dict:
        """
        Subset and return a field from CMEMS.
        Requires copernicusmarine to be installed and credentials configured.
        """
        try:
            import copernicusmarine  # type: ignore
        except ImportError:
            logger.error("copernicusmarine not installed. Run: pip install copernicusmarine")
            return {}

        bbox = kwargs.get("bbox", {})
        try:
            ds = copernicusmarine.open_dataset(
                dataset_id=self.PRODUCTS["global_physics_reanalysis"],
                variables=[variable],
                minimum_longitude=bbox.get("lon_min", 40),
                maximum_longitude=bbox.get("lon_max", 100),
                minimum_latitude=bbox.get("lat_min", -30),
                maximum_latitude=bbox.get("lat_max", 30),
                minimum_depth=depth,
                maximum_depth=depth,
                start_datetime=str(time),
                end_datetime=str(time),
            )
            return {"dataset": ds, "variable": variable}
        except Exception as exc:
            logger.error("CMEMS fetch failed: %s", exc)
            return {}

    def capabilities(self) -> dict:
        caps = super().capabilities()
        caps.update({"supports_fields": True, "supports_profiles": False})
        return caps
