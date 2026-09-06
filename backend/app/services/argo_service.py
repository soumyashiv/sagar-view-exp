"""
Argo observation service.
Primary: Argovis REST API (https://argovis.colorado.edu)
Fallback: bundled synthetic Argo profiles (demo mode).
"""
from __future__ import annotations
import logging
import math
from typing import Optional

import httpx

from app.config import settings
from app.models.schemas import ObservationPlatform, OceanProfile, ProfileLevel
from app.services import cache_service

logger = logging.getLogger(__name__)

ARGOVIS_BASE = settings.argovis_base_url


async def list_platforms(
    lon_min: float,
    lon_max: float,
    lat_min: float,
    lat_max: float,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    max_platforms: int = 100,
) -> list[ObservationPlatform]:
    """Return Argo platforms within a bounding box."""

    cache_key = cache_service.make_key(
        "obs_list", lon_min, lon_max, lat_min, lat_max, date_start, date_end
    )
    cached = cache_service.cache_get(cache_key)
    if cached:
        return [ObservationPlatform(**p) for p in cached]

    if settings.demo_mode:
        platforms = _demo_platforms()
        # Filter to bbox
        platforms = [
            p for p in platforms
            if lon_min <= p.longitude <= lon_max and lat_min <= p.latitude <= lat_max
        ]
    else:
        platforms = await _fetch_argovis_platforms(
            lon_min, lon_max, lat_min, lat_max, date_start, date_end, max_platforms
        )

    cache_service.cache_set(
        cache_key,
        [p.model_dump() for p in platforms],
        ttl=settings.obs_cache_ttl,
    )
    return platforms


async def get_profile(platform_id: str) -> Optional[OceanProfile]:
    """Return a full depth profile for a platform."""
    cache_key = cache_service.make_key("profile", platform_id)
    cached = cache_service.cache_get(cache_key)
    if cached:
        return OceanProfile(**cached)

    if settings.demo_mode:
        # Only return a demo profile if the platform_id is in our demo data
        known_ids = {p["id"] for p in _DEMO_PLATFORM_DATA}
        if platform_id not in known_ids:
            return None
        profile = _demo_profile(platform_id)
    else:
        profile = await _fetch_argovis_profile(platform_id)

    if profile:
        cache_service.cache_set(cache_key, profile.model_dump(), ttl=settings.obs_cache_ttl)
    return profile


# ── Argovis fetch ─────────────────────────────────────────────────────────────

async def _fetch_argovis_platforms(
    lon_min, lon_max, lat_min, lat_max, date_start, date_end, max_platforms
) -> list[ObservationPlatform]:
    """Call Argovis /argo endpoint."""
    polygon = [
        [lon_min, lat_min], [lon_max, lat_min],
        [lon_max, lat_max], [lon_min, lat_max], [lon_min, lat_min]
    ]
    params: dict = {
        "polygon": str(polygon).replace(" ", ""),
        "data": "temperature,salinity",
    }
    if date_start:
        params["startDate"] = date_start
    if date_end:
        params["endDate"] = date_end

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{ARGOVIS_BASE}/argo", params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("Argovis fetch failed (%s); using demo data", exc)
        return _demo_platforms()

    platforms = []
    for record in data[:max_platforms]:
        try:
            geo = record.get("geolocation", {}).get("coordinates", [0, 0])
            platforms.append(ObservationPlatform(
                platform_id=str(record.get("_id", "unknown")),
                platform_type="argo",
                latitude=geo[1],
                longitude=geo[0],
                timestamp=record.get("timestamp", ""),
                depth_min=0.0,
                depth_max=2000.0,
                variables=["temperature", "salinity"],
                wmo=str(record.get("platform_number", "")),
                cycle_number=record.get("cycle_number"),
            ))
        except Exception:
            continue
    return platforms


async def _fetch_argovis_profile(platform_id: str) -> Optional[OceanProfile]:
    """Fetch single profile from Argovis."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{ARGOVIS_BASE}/argo/{platform_id}")
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                data = data[0]
    except Exception as exc:
        logger.warning("Argovis profile fetch failed (%s); using demo profile", exc)
        return _demo_profile(platform_id)

    try:
        geo = data.get("geolocation", {}).get("coordinates", [0, 0])
        measurements = data.get("measurements", [])
        levels = []
        for m in measurements:
            levels.append(ProfileLevel(
                depth=float(m.get("pres", 0)),
                temperature=m.get("temp"),
                salinity=m.get("psal"),
                pressure=m.get("pres"),
            ))

        return OceanProfile(
            platform_id=platform_id,
            platform_type="argo",
            latitude=geo[1],
            longitude=geo[0],
            timestamp=data.get("timestamp", ""),
            levels=levels,
            variables=["temperature", "salinity"],
            metadata={"source": "argovis", "wmo": data.get("platform_number", "")},
        )
    except Exception as exc:
        logger.error("Profile parse error: %s", exc)
        return _demo_profile(platform_id)


# ── Synthetic demo data ────────────────────────────────────────────────────────

import numpy as np

_RNG = np.random.default_rng(42)

# Generate 40 deterministic Argo platform locations in Indian Ocean
_DEMO_PLATFORM_DATA = []
for i in range(40):
    rng = np.random.default_rng(i + 100)
    lon = float(rng.uniform(45, 95))
    lat = float(rng.uniform(-25, 25))
    year = 2023
    month = int(rng.integers(1, 13))
    day = int(rng.integers(1, 28))
    _DEMO_PLATFORM_DATA.append({
        "id": f"ARGO_{6900000 + i * 37}",
        "lon": lon,
        "lat": lat,
        "timestamp": f"{year}-{month:02d}-{day:02d}T00:00:00Z",
        "wmo": str(6900000 + i * 37),
        "cycle": int(rng.integers(1, 200)),
    })


def _demo_platforms() -> list[ObservationPlatform]:
    return [
        ObservationPlatform(
            platform_id=p["id"],
            platform_type="argo",
            latitude=p["lat"],
            longitude=p["lon"],
            timestamp=p["timestamp"],
            depth_min=5.0,
            depth_max=2000.0,
            variables=["temperature", "salinity"],
            wmo=p["wmo"],
            cycle_number=p["cycle"],
        )
        for p in _DEMO_PLATFORM_DATA
    ]


def _demo_profile(platform_id: str) -> OceanProfile:
    # Find matching demo data
    match = next((p for p in _DEMO_PLATFORM_DATA if p["id"] == platform_id), _DEMO_PLATFORM_DATA[0])
    lat, lon = match["lat"], match["lon"]

    # Realistic depth levels
    depths = [5, 10, 20, 30, 50, 75, 100, 125, 150, 200,
              300, 400, 500, 600, 750, 1000, 1250, 1500, 1750, 2000]

    rng = np.random.default_rng(hash(platform_id) % (2**32))
    surface_temp = 28.0 + rng.uniform(-2, 2) - abs(lat) * 0.3

    levels = []
    for d in depths:
        # Temperature: warm surface, thermocline between 50-200m, cold deep
        if d < 50:
            T = surface_temp - d * 0.05
        elif d < 300:
            T = surface_temp - 2.5 - (d - 50) * 0.08
        else:
            T = max(2.0, surface_temp - 22 - (d - 300) * 0.003)
        T += float(rng.normal(0, 0.3))

        # Salinity: surface fresher, max ~100-200m, decrease deep
        if d < 20:
            S = 34.5 + rng.uniform(-0.5, 0.5)
        elif d < 200:
            S = 35.2 + (d - 20) / 180 * 0.5 + rng.uniform(-0.1, 0.1)
        else:
            S = 35.7 - (d - 200) / 1800 * 1.0 + rng.uniform(-0.1, 0.1)

        levels.append(ProfileLevel(
            depth=float(d),
            temperature=round(float(T), 3),
            salinity=round(float(S), 3),
            pressure=float(d),
        ))

    return OceanProfile(
        platform_id=platform_id,
        platform_type="argo",
        latitude=lat,
        longitude=lon,
        timestamp=match["timestamp"],
        levels=levels,
        variables=["temperature", "salinity"],
        metadata={
            "source": "demo",
            "wmo": match["wmo"],
            "cycle": match["cycle"],
            "n_levels": len(levels),
        },
    )
