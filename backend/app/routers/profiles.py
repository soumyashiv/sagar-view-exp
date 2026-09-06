"""Profiles router — individual platform profiles and collocation."""
from fastapi import APIRouter, Query, HTTPException
from app.models.schemas import OceanProfile, CollocateResult
from app.services import argo_service, collocate_service

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("/{platform_id}", response_model=OceanProfile)
async def get_profile(platform_id: str):
    """Return full depth profile for an observation platform."""
    profile = await argo_service.get_profile(platform_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Platform '{platform_id}' not found")
    return profile


@router.get("/{platform_id}/collocate", response_model=CollocateResult)
async def collocate_profile(
    platform_id: str,
    dataset_id: str = Query("indian_ocean_demo"),
    variable: str = Query("thetao"),
    time_idx: int = Query(0),
):
    """
    Collocate model data with an observation profile.
    Returns depth-by-depth model vs. observed comparison.
    """
    profile = await argo_service.get_profile(platform_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Platform '{platform_id}' not found")

    try:
        result = collocate_service.collocate(
            dataset_id=dataset_id,
            variable=variable,
            profile=profile,
            time_idx=time_idx,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return result
