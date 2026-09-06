#!/usr/bin/env python3
"""
Generate deterministic synthetic Indian Ocean NetCDF demo dataset for SAGAR-VIEW.

Produces: backend/data/demo/indian_ocean_demo.nc

Grid:
  lon: 40–100°E  step 0.25° → 241 points
  lat: -30–30°N  step 0.25° → 241 points
  depth: 20 levels (5–2000m)
  time: 12 monthly steps (2023-01-01 to 2023-12-01)

Variables (CF-compliant):
  thetao  — potential temperature (°C)
  so      — salinity (PSU)
  uo      — eastward velocity (m/s)
  vo      — northward velocity (m/s)
  zos     — sea surface height (m)

Run:
  cd backend
  python scripts/generate_demo_data.py
"""
import sys
from pathlib import Path

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import netCDF4 as nc
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ── Grid definition ────────────────────────────────────────────────────────────

LON_MIN, LON_MAX, LON_STEP = 40.0, 100.25, 0.25
LAT_MIN, LAT_MAX, LAT_STEP = -30.0, 30.25, 0.25

LONS = np.arange(LON_MIN, LON_MAX, LON_STEP)   # 241
LATS = np.arange(LAT_MIN, LAT_MAX, LAT_STEP)   # 241
DEPTHS = np.array([
    5, 10, 15, 20, 30, 50, 75, 100, 125, 150,
    200, 300, 400, 500, 600, 750, 1000, 1250, 1500, 2000
], dtype=np.float32)

N_TIME = 12
START_DATE = datetime(2023, 1, 1)
TIMES = [START_DATE + timedelta(days=30 * i) for i in range(N_TIME)]

RNG = np.random.default_rng(42)

OUT_PATH = Path(__file__).parent.parent / "data" / "demo" / "indian_ocean_demo.nc"


# ── Physics ────────────────────────────────────────────────────────────────────

def make_temperature(lon_grid, lat_grid, depth: float, month_idx: int) -> np.ndarray:
    """
    Realistic synthetic temperature field.
    Warm tropical, cool subtropical, thermocline with depth.
    """
    # Base temperature: warm tropics, cooler at high latitudes
    base = 28.0 - np.abs(lat_grid) * 0.4 - np.abs(lat_grid - 5) * 0.05

    # Seasonal cycle: warmer in NH summer (month 6-8)
    seasonal = 1.5 * np.cos(2 * np.pi * (month_idx - 7) / 12) * (1 - np.abs(lat_grid) / 30)

    # Depth attenuation: thermocline
    if depth <= 20:
        depth_factor = 1.0
    elif depth <= 200:
        depth_factor = 1.0 - 0.6 * (depth - 20) / 180
    elif depth <= 1000:
        depth_factor = 0.4 - 0.35 * (depth - 200) / 800
    else:
        depth_factor = 0.05 - 0.04 * (depth - 1000) / 1000

    T = base * depth_factor + seasonal * max(depth_factor, 0.1)

    # Arabian Sea upwelling signature (NW Indian Ocean in summer)
    if month_idx in (5, 6, 7, 8):
        mask = (lon_grid >= 55) & (lon_grid <= 65) & (lat_grid >= 8) & (lat_grid <= 20)
        T = np.where(mask, T - 3.0 * (1 - depth / 200) * (month_idx == 7 or month_idx == 6), T)

    # Bay of Bengal warm pool (eastern, surface)
    if depth < 50:
        bob_mask = (lon_grid >= 80) & (lon_grid <= 95) & (lat_grid >= 5) & (lat_grid <= 20)
        T = np.where(bob_mask, T + 1.5, T)

    noise = RNG.normal(0, 0.15, T.shape)
    return np.clip(T + noise, 2.0, 33.0).astype(np.float32)


def make_salinity(lon_grid, lat_grid, depth: float, month_idx: int) -> np.ndarray:
    """Realistic salinity field."""
    # Surface: Bay of Bengal fresh, Arabian Sea salty
    surface_base = np.where(
        (lon_grid >= 80) & (lat_grid >= 5),
        33.5,  # Bay of Bengal (fresh rivers)
        35.2,  # Arabian Sea / open ocean
    )

    # Subtropical salinity maximum
    sub_lat_mask = (np.abs(lat_grid) >= 20) & (np.abs(lat_grid) <= 30)
    surface_base = np.where(sub_lat_mask, surface_base + 0.8, surface_base)

    # Depth profile: surface freshening, subsurface max, AAIW tongue
    if depth <= 30:
        depth_offset = -0.3 * (1 - depth / 30)
    elif depth <= 200:
        depth_offset = 0.5 * (depth - 30) / 170
    elif depth <= 700:
        depth_offset = 0.5 - 1.2 * (depth - 200) / 500   # AAIW
    else:
        depth_offset = -0.7 + 0.3 * (depth - 700) / 1300

    S = surface_base + depth_offset
    noise = RNG.normal(0, 0.05, S.shape)
    return np.clip(S + noise, 30.0, 37.5).astype(np.float32)


def make_velocity(lon_grid, lat_grid, depth: float, month_idx: int) -> tuple[np.ndarray, np.ndarray]:
    """Synthetic current velocities."""
    # Base: westward South Equatorial Current, eastward SECC
    u_base = np.where(np.abs(lat_grid) < 5, 0.15, -0.1)
    v_base = np.zeros_like(u_base)

    # Somali Current (western boundary, NH summer)
    if month_idx in (5, 6, 7, 8):
        somali = (lon_grid >= 40) & (lon_grid <= 52) & (lat_grid >= -5) & (lat_grid <= 15)
        u_somali = 0.8 * (1 - depth / 300) * np.exp(-((lat_grid - 8) ** 2) / 25)
        v_somali = 1.2 * (1 - depth / 300) * np.exp(-((lon_grid - 45) ** 2) / 16)
        u_base = np.where(somali, u_somali, u_base)
        v_base = np.where(somali, v_somali, v_base)

    # Agulhas Current (southwestern boundary)
    agulhas = (lon_grid >= 40) & (lon_grid <= 55) & (lat_grid >= -35) & (lat_grid <= -25)
    u_base = np.where(agulhas, -0.4 * (1 - depth / 500), u_base)
    v_base = np.where(agulhas, -0.6 * (1 - depth / 500), v_base)

    # Depth attenuation
    depth_factor = max(0, 1 - depth / 800)

    noise_u = RNG.normal(0, 0.02, u_base.shape)
    noise_v = RNG.normal(0, 0.02, v_base.shape)

    u = (u_base * depth_factor + noise_u).astype(np.float32)
    v = (v_base * depth_factor + noise_v).astype(np.float32)
    return u, v


def make_ssh(lon_grid, lat_grid, month_idx: int) -> np.ndarray:
    """Sea surface height anomaly."""
    # Seasonal thermosteric signal
    ssh = 0.1 * np.cos(2 * np.pi * (month_idx - 4) / 12) * np.cos(np.deg2rad(lat_grid))

    # Subtropical high-pressure lens
    ssh += 0.3 * np.exp(-(lat_grid ** 2 / 200 + (lon_grid - 70) ** 2 / 800))

    # Somali upwelling trough (summer)
    if month_idx in (5, 6, 7, 8):
        ssh -= 0.15 * np.exp(-((lon_grid - 52) ** 2 / 25 + (lat_grid - 10) ** 2 / 16))

    noise = RNG.normal(0, 0.01, ssh.shape)
    return (ssh + noise).astype(np.float32)


# ── Writer ─────────────────────────────────────────────────────────────────────

def generate() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    log.info("Writing to %s", OUT_PATH)

    LON_GRID, LAT_GRID = np.meshgrid(LONS, LATS)  # (241, 241)

    with nc.Dataset(OUT_PATH, "w", format="NETCDF4") as ds:
        # Global attributes (CF-1.8)
        ds.Conventions = "CF-1.8"
        ds.title = "SAGAR-VIEW Indian Ocean Demo Dataset"
        ds.institution = "SAGAR-VIEW MVP (SIH26067)"
        ds.source = "Synthetic data generated for demonstration purposes"
        ds.history = f"Created {datetime.utcnow().isoformat()}Z by generate_demo_data.py"
        ds.references = "https://github.com/sagarview"
        ds.comment = (
            "Synthetic 1/4-degree Indian Ocean dataset. "
            "NOT real observational or model data."
        )
        ds.geospatial_lat_min = float(LATS.min())
        ds.geospatial_lat_max = float(LATS.max())
        ds.geospatial_lon_min = float(LONS.min())
        ds.geospatial_lon_max = float(LONS.max())
        ds.time_coverage_start = TIMES[0].isoformat()
        ds.time_coverage_end = TIMES[-1].isoformat()

        # Dimensions
        ds.createDimension("longitude", len(LONS))
        ds.createDimension("latitude", len(LATS))
        ds.createDimension("depth", len(DEPTHS))
        ds.createDimension("time", N_TIME)

        # Coordinate variables
        lon_v = ds.createVariable("longitude", "f4", ("longitude",))
        lon_v[:] = LONS
        lon_v.units = "degrees_east"
        lon_v.long_name = "Longitude"
        lon_v.standard_name = "longitude"
        lon_v.axis = "X"

        lat_v = ds.createVariable("latitude", "f4", ("latitude",))
        lat_v[:] = LATS
        lat_v.units = "degrees_north"
        lat_v.long_name = "Latitude"
        lat_v.standard_name = "latitude"
        lat_v.axis = "Y"

        dep_v = ds.createVariable("depth", "f4", ("depth",))
        dep_v[:] = DEPTHS
        dep_v.units = "m"
        dep_v.long_name = "Depth"
        dep_v.standard_name = "depth"
        dep_v.positive = "down"
        dep_v.axis = "Z"

        time_v = ds.createVariable("time", "f8", ("time",))
        # Days since 2023-01-01
        time_v[:] = np.array([(t - START_DATE).days for t in TIMES], dtype=np.float64)
        time_v.units = "days since 2023-01-01 00:00:00"
        time_v.long_name = "Time"
        time_v.standard_name = "time"
        time_v.calendar = "gregorian"
        time_v.axis = "T"

        # Data variables
        def _create_var(name, long_name, units, standard_name, valid_range, fill=-9999.0):
            v = ds.createVariable(
                name, "f4", ("time", "depth", "latitude", "longitude"),
                zlib=True, complevel=4, fill_value=np.float32(fill),
                chunksizes=(1, 1, 60, 60),
            )
            v.long_name = long_name
            v.units = units
            v.standard_name = standard_name
            v.valid_min = valid_range[0]
            v.valid_max = valid_range[1]
            v.grid_mapping = "crs"
            return v

        thetao_v = _create_var("thetao", "Sea Water Potential Temperature", "degrees_C",
                               "sea_water_potential_temperature", (2, 33))
        so_v     = _create_var("so", "Sea Water Salinity", "1e-3",
                               "sea_water_salinity", (30, 38))
        uo_v     = _create_var("uo", "Sea Water X Velocity", "m s-1",
                               "eastward_sea_water_velocity", (-2, 2))
        vo_v     = _create_var("vo", "Sea Water Y Velocity", "m s-1",
                               "northward_sea_water_velocity", (-2, 2))

        # SSH (time, lat, lon only)
        zos_v = ds.createVariable(
            "zos", "f4", ("time", "latitude", "longitude"),
            zlib=True, complevel=4, fill_value=-9999.0, chunksizes=(1, 60, 60),
        )
        zos_v.long_name = "Sea Surface Height Above Geoid"
        zos_v.units = "m"
        zos_v.standard_name = "sea_surface_height_above_geoid"

        # CRS
        crs_v = ds.createVariable("crs", "i4")
        crs_v.grid_mapping_name = "latitude_longitude"
        crs_v.epsg_code = "EPSG:4326"

        log.info("Filling variables (time=%d, depth=%d, lat=%d, lon=%d)...",
                 N_TIME, len(DEPTHS), len(LATS), len(LONS))

        for t_idx, t_date in enumerate(TIMES):
            month_idx = t_date.month - 1  # 0-based
            log.info("  Time step %d/%d (%s)", t_idx + 1, N_TIME, t_date.strftime("%Y-%m"))

            for d_idx, depth in enumerate(DEPTHS):
                T = make_temperature(LON_GRID, LAT_GRID, float(depth), month_idx)
                S = make_salinity(LON_GRID, LAT_GRID, float(depth), month_idx)
                U, V = make_velocity(LON_GRID, LAT_GRID, float(depth), month_idx)

                thetao_v[t_idx, d_idx, :, :] = T
                so_v[t_idx, d_idx, :, :] = S
                uo_v[t_idx, d_idx, :, :] = U
                vo_v[t_idx, d_idx, :, :] = V

            zos_v[t_idx, :, :] = make_ssh(LON_GRID, LAT_GRID, month_idx)

    log.info("Done. File: %s (%.1f MB)", OUT_PATH, OUT_PATH.stat().st_size / 1e6)


if __name__ == "__main__":
    generate()
