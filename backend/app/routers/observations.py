"""Observations router — Argo platforms and platform lists."""
from fastapi import APIRouter, Query
from app.models.schemas import ObservationPlatform
from app.services import argo_service

router = APIRouter(prefix="/api/observations", tags=["observations"])


@router.get("", response_model=list[ObservationPlatform])
async def list_observations(
    lon_min: float = Query(40.0),
    lon_max: float = Query(100.0),
    lat_min: float = Query(-30.0),
    lat_max: float = Query(30.0),
    date_start: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    date_end: str | None = Query(None),
    max_platforms: int = Query(100, le=500),
):
    """List observation platforms (Argo floats) within bounding box."""
    return await argo_service.list_platforms(
        lon_min=lon_min,
        lon_max=lon_max,
        lat_min=lat_min,
        lat_max=lat_max,
        date_start=date_start,
        date_end=date_end,
        max_platforms=max_platforms,
    )
