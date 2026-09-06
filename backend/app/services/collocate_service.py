"""
Collocation service: interpolates model field at observation location
and computes model-observation differences.
"""
from __future__ import annotations
import logging
import math
from typing import Optional

import numpy as np

from app.models.schemas import CollocateResult, CollocateLevel, OceanProfile
from app.services import dataset_service

logger = logging.getLogger(__name__)


def collocate(
    dataset_id: str,
    variable: str,
    profile: OceanProfile,
    time_idx: int = 0,
) -> CollocateResult:
    """
    Collocate model profile at observation location.
    Returns level-by-level comparison.
    """
    # Get model vertical profile at nearest grid point
    try:
        model_levels = dataset_service.get_model_profile(
            dataset_id=dataset_id,
            variable=variable,
            lat=profile.latitude,
            lon=profile.longitude,
            time_idx=time_idx,
        )
    except Exception as exc:
        logger.error("Model profile extraction failed: %s", exc)
        model_levels = []

    # Map model levels to a dict by depth
    model_by_depth: dict[float, Optional[float]] = {
        m["depth"]: m["value"] for m in model_levels
    }
    model_depths = sorted(model_by_depth.keys())

    # Get observation values for the variable
    obs_field = variable  # e.g. "thetao" → temperature
    obs_field_map = {
        "thetao": "temperature",
        "so": "salinity",
        "temperature": "temperature",
        "salinity": "salinity",
    }
    obs_attr = obs_field_map.get(variable, variable)

    levels_out: list[CollocateLevel] = []
    diffs: list[float] = []

    for obs_level in profile.levels:
        obs_val = getattr(obs_level, obs_attr, None)
        obs_depth = obs_level.depth

        # Interpolate model at obs depth
        if model_depths:
            model_val = _interpolate_profile(model_by_depth, model_depths, obs_depth)
        else:
            model_val = None

        diff = None
        if model_val is not None and obs_val is not None:
            diff = round(model_val - obs_val, 4)
            diffs.append(abs(diff))

        levels_out.append(CollocateLevel(
            depth=obs_depth,
            model_value=round(model_val, 4) if model_val is not None else None,
            obs_value=round(obs_val, 4) if obs_val is not None else None,
            difference=diff,
        ))

    mad = round(float(np.mean(diffs)), 4) if diffs else 0.0

    var_meta = dataset_service.VARIABLE_META.get(variable)
    units = var_meta.units if var_meta else ""

    return CollocateResult(
        platform_id=profile.platform_id,
        variable=variable,
        units=units,
        latitude=profile.latitude,
        longitude=profile.longitude,
        timestamp=profile.timestamp,
        levels=levels_out,
        mean_absolute_difference=mad,
        n_matched=len(diffs),
        note=(
            "Simple nearest-grid-point collocation. "
            "Not a formal scientific validation."
        ),
    )


def _interpolate_profile(
    profile_dict: dict[float, Optional[float]],
    sorted_depths: list[float],
    target_depth: float,
) -> Optional[float]:
    """Linear interpolation of model profile at target depth."""
    if not sorted_depths:
        return None

    # Exact match
    if target_depth in profile_dict:
        return profile_dict[target_depth]

    # Find bracketing levels
    lo_depth = max((d for d in sorted_depths if d <= target_depth), default=None)
    hi_depth = min((d for d in sorted_depths if d >= target_depth), default=None)

    if lo_depth is None:
        return profile_dict.get(sorted_depths[0])
    if hi_depth is None:
        return profile_dict.get(sorted_depths[-1])

    lo_val = profile_dict[lo_depth]
    hi_val = profile_dict[hi_depth]

    if lo_val is None or hi_val is None:
        return lo_val or hi_val

    if lo_depth == hi_depth:
        return lo_val

    t = (target_depth - lo_depth) / (hi_depth - lo_depth)
    return lo_val + t * (hi_val - lo_val)
