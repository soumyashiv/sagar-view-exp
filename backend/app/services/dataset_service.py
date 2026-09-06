"""
Dataset service: opens NetCDF files with xarray, performs subsetting,
validates CF conventions, and returns browser-friendly payloads.
"""
from __future__ import annotations
import math
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import xarray as xr

from app.config import settings
from app.models.schemas import DatasetInfo, VariableMeta, OceanField, CurrentField
from app.services import cache_service

logger = logging.getLogger(__name__)

# ── Variable catalogue ─────────────────────────────────────────────────────────

VARIABLE_META: dict[str, VariableMeta] = {
    "thetao": VariableMeta(
        name="thetao",
        long_name="Sea Water Potential Temperature",
        units="°C",
        standard_name="sea_water_potential_temperature",
        colormap_hint="thermal",
    ),
    "so": VariableMeta(
        name="so",
        long_name="Sea Water Salinity",
        units="PSU",
        standard_name="sea_water_salinity",
        colormap_hint="haline",
    ),
    "uo": VariableMeta(
        name="uo",
        long_name="Sea Water X Velocity",
        units="m/s",
        standard_name="eastward_sea_water_velocity",
        colormap_hint="speed",
    ),
    "vo": VariableMeta(
        name="vo",
        long_name="Sea Water Y Velocity",
        units="m/s",
        standard_name="northward_sea_water_velocity",
        colormap_hint="speed",
    ),
    "zos": VariableMeta(
        name="zos",
        long_name="Sea Surface Height",
        units="m",
        standard_name="sea_surface_height_above_geoid",
        colormap_hint="balance",
    ),
}


# ── Dataset registry ──────────────────────────────────────────────────────────

class DatasetRegistry:
    """Manages open xarray datasets."""

    def __init__(self):
        self._datasets: dict[str, xr.Dataset] = {}

    def load(self, dataset_id: str, path: Path) -> xr.Dataset:
        if dataset_id not in self._datasets:
            logger.info("Loading dataset %s from %s", dataset_id, path)
            ds = xr.open_dataset(path, engine="netcdf4")
            self._datasets[dataset_id] = ds
        return self._datasets[dataset_id]

    def get(self, dataset_id: str) -> Optional[xr.Dataset]:
        return self._datasets.get(dataset_id)

    def close_all(self):
        for ds in self._datasets.values():
            ds.close()
        self._datasets.clear()


registry = DatasetRegistry()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_dim(ds: xr.Dataset, candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in ds.dims or c in ds.coords:
            return c
    return None


def _to_python_float(x) -> float:
    v = float(x)
    return v if math.isfinite(v) else None


def _sanitize_array(arr: np.ndarray) -> list:
    flat = arr.astype(float).ravel()
    result = []
    for v in flat:
        if np.isnan(v) or np.isinf(v):
            result.append(None)
        else:
            result.append(round(float(v), 4))
    return result


# ── Public API ─────────────────────────────────────────────────────────────────

def get_demo_path() -> Path:
    return settings.demo_dir / settings.demo_nc_filename


def list_datasets() -> list[DatasetInfo]:
    """Return catalogue of available datasets."""
    demo_path = get_demo_path()
    if not demo_path.exists():
        logger.warning("Demo NetCDF not found at %s — run generate_demo_data.py", demo_path)
        return []

    ds = registry.load("indian_ocean_demo", demo_path)

    lon_dim = _detect_dim(ds, ["longitude", "lon", "x"])
    lat_dim = _detect_dim(ds, ["latitude", "lat", "y"])
    depth_dim = _detect_dim(ds, ["depth", "lev", "z", "deptht"])
    time_dim = _detect_dim(ds, ["time"])

    lons = ds[lon_dim].values
    lats = ds[lat_dim].values
    depths = ds[depth_dim].values if depth_dim else [0.0]
    times = ds[time_dim].values if time_dim else []

    avail_vars = [VARIABLE_META[v] for v in VARIABLE_META if v in ds.data_vars]

    time_strs = []
    for t in times:
        try:
            time_strs.append(str(np.datetime_as_string(t, unit="D")))
        except Exception:
            time_strs.append(str(t))

    return [
        DatasetInfo(
            id="indian_ocean_demo",
            name="Indian Ocean Demo — SAGAR-VIEW",
            source="demo",
            description=(
                "Synthetic 1/4° Indian Ocean dataset (40–100°E, 30°S–30°N), "
                "12 monthly time steps, 20 depth levels. Temperature, salinity, "
                "currents, and sea surface height."
            ),
            lon_min=float(lons.min()),
            lon_max=float(lons.max()),
            lat_min=float(lats.min()),
            lat_max=float(lats.max()),
            depth_levels=[round(float(d), 2) for d in depths],
            time_steps=time_strs,
            variables=avail_vars,
            resolution_deg=0.25,
        )
    ]


def get_ocean_field(
    dataset_id: str,
    variable: str,
    depth_idx: int = 0,
    time_idx: int = 0,
    lon_min: float = 40.0,
    lon_max: float = 100.0,
    lat_min: float = -30.0,
    lat_max: float = 30.0,
) -> OceanField:
    """Return a 2-D field at a specific depth and time step."""

    cache_key = cache_service.make_key(
        "field", dataset_id, variable, depth_idx, time_idx,
        lon_min, lon_max, lat_min, lat_max
    )
    cached = cache_service.cache_get(cache_key)
    if cached:
        return OceanField(**cached)

    ds = _open_dataset(dataset_id)
    lon_dim = _detect_dim(ds, ["longitude", "lon", "x"])
    lat_dim = _detect_dim(ds, ["latitude", "lat", "y"])
    depth_dim = _detect_dim(ds, ["depth", "lev", "z", "deptht"])
    time_dim = _detect_dim(ds, ["time"])

    # Spatial subset
    ds_sub = ds.sel(
        {lon_dim: slice(lon_min, lon_max), lat_dim: slice(lat_min, lat_max)}
    )

    # Select depth
    da = ds_sub[variable]
    if depth_dim and depth_dim in da.dims:
        da = da.isel({depth_dim: depth_idx})
    if time_dim and time_dim in da.dims:
        da = da.isel({time_dim: time_idx})

    arr = da.values.squeeze()
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)

    # Retrieve coordinate arrays
    lons = ds_sub[lon_dim].values
    lats = ds_sub[lat_dim].values
    depths = ds[depth_dim].values if depth_dim else np.array([0.0])
    times = ds[time_dim].values if time_dim else []

    depth_val = float(depths[depth_idx]) if len(depths) > depth_idx else 0.0
    time_str = str(np.datetime_as_string(times[time_idx], unit="D")) if len(times) > time_idx else "N/A"

    valid = arr[~np.isnan(arr)]
    vmin = float(np.percentile(valid, 2)) if len(valid) else 0.0
    vmax = float(np.percentile(valid, 98)) if len(valid) else 1.0

    var_meta = VARIABLE_META.get(variable, VariableMeta(
        name=variable, long_name=variable, units="", standard_name="", colormap_hint="viridis"
    ))

    payload = OceanField(
        dataset_id=dataset_id,
        variable=variable,
        units=var_meta.units,
        depth_m=depth_val,
        time_step=time_str,
        lon_min=float(lons.min()),
        lon_max=float(lons.max()),
        lat_min=float(lats.min()),
        lat_max=float(lats.max()),
        n_lon=len(lons),
        n_lat=len(lats),
        values=_sanitize_array(arr),
        vmin=round(vmin, 4),
        vmax=round(vmax, 4),
        colormap_hint=var_meta.colormap_hint,
    )

    cache_service.cache_set(cache_key, payload.model_dump(), ttl=settings.field_cache_ttl)
    return payload


def get_current_field(
    dataset_id: str,
    depth_idx: int = 0,
    time_idx: int = 0,
    lon_min: float = 40.0,
    lon_max: float = 100.0,
    lat_min: float = -30.0,
    lat_max: float = 30.0,
) -> CurrentField:
    """Return u/v current vector field."""

    cache_key = cache_service.make_key(
        "current", dataset_id, depth_idx, time_idx,
        lon_min, lon_max, lat_min, lat_max
    )
    cached = cache_service.cache_get(cache_key)
    if cached:
        return CurrentField(**cached)

    ds = _open_dataset(dataset_id)
    lon_dim = _detect_dim(ds, ["longitude", "lon", "x"])
    lat_dim = _detect_dim(ds, ["latitude", "lat", "y"])
    depth_dim = _detect_dim(ds, ["depth", "lev", "z", "deptht"])
    time_dim = _detect_dim(ds, ["time"])

    ds_sub = ds.sel(
        {lon_dim: slice(lon_min, lon_max), lat_dim: slice(lat_min, lat_max)}
    )

    def _extract(varname):
        da = ds_sub[varname]
        if depth_dim and depth_dim in da.dims:
            da = da.isel({depth_dim: depth_idx})
        if time_dim and time_dim in da.dims:
            da = da.isel({time_dim: time_idx})
        return da.values.squeeze()

    u = _extract("uo") if "uo" in ds_sub.data_vars else np.zeros((10, 10))
    v = _extract("vo") if "vo" in ds_sub.data_vars else np.zeros((10, 10))

    lons = ds_sub[lon_dim].values
    lats = ds_sub[lat_dim].values
    depths = ds[depth_dim].values if depth_dim else np.array([0.0])
    times = ds[time_dim].values if time_dim else []

    depth_val = float(depths[depth_idx]) if len(depths) > depth_idx else 0.0
    time_str = str(np.datetime_as_string(times[time_idx], unit="D")) if len(times) > time_idx else "N/A"

    speed = np.sqrt(u**2 + v**2)
    speed_max = float(np.nanmax(speed)) if np.any(~np.isnan(speed)) else 1.0

    payload = CurrentField(
        dataset_id=dataset_id,
        depth_m=depth_val,
        time_step=time_str,
        lon_min=float(lons.min()),
        lon_max=float(lons.max()),
        lat_min=float(lats.min()),
        lat_max=float(lats.max()),
        n_lon=len(lons),
        n_lat=len(lats),
        u_values=_sanitize_array(u),
        v_values=_sanitize_array(v),
        speed_max=round(speed_max, 4),
    )

    cache_service.cache_set(cache_key, payload.model_dump(), ttl=settings.field_cache_ttl)
    return payload


def get_model_profile(
    dataset_id: str,
    variable: str,
    lat: float,
    lon: float,
    time_idx: int = 0,
) -> list[dict]:
    """Extract a vertical profile at the nearest grid point."""
    ds = _open_dataset(dataset_id)
    lon_dim = _detect_dim(ds, ["longitude", "lon", "x"])
    lat_dim = _detect_dim(ds, ["latitude", "lat", "y"])
    depth_dim = _detect_dim(ds, ["depth", "lev", "z", "deptht"])
    time_dim = _detect_dim(ds, ["time"])

    da = ds[variable]
    if time_dim and time_dim in da.dims:
        da = da.isel({time_dim: time_idx})

    da_point = da.sel({lon_dim: lon, lat_dim: lat}, method="nearest")

    depths = ds[depth_dim].values if depth_dim else [0.0]
    values = da_point.values.ravel()

    return [
        {"depth": float(depths[i]), "value": _to_python_float(values[i])}
        for i in range(len(depths))
    ]


def _open_dataset(dataset_id: str) -> xr.Dataset:
    demo_path = get_demo_path()
    if not demo_path.exists():
        raise FileNotFoundError(
            f"Demo NetCDF not found at {demo_path}. "
            "Run: python backend/scripts/generate_demo_data.py"
        )
    return registry.load(dataset_id, demo_path)
