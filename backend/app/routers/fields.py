"""Ocean field and current vector routers."""
from fastapi import APIRouter, Query, HTTPException
from app.models.schemas import OceanField, CurrentField
from app.services import dataset_service

router = APIRouter(prefix="/api", tags=["fields"])


@router.get("/fields/{dataset_id}", response_model=OceanField)
def get_field(
    dataset_id: str,
    variable: str = Query("thetao", description="Variable name (thetao, so, zos)"),
    depth_idx: int = Query(0, ge=0, description="Depth level index"),
    time_idx: int = Query(0, ge=0, description="Time step index"),
    lon_min: float = Query(40.0),
    lon_max: float = Query(100.0),
    lat_min: float = Query(-30.0),
    lat_max: float = Query(30.0),
):
    """
    Return a 2D ocean field at a specific depth and time step.
    Values are flattened row-major (lat-major). NaN → null.
    """
    try:
        return dataset_service.get_ocean_field(
            dataset_id=dataset_id,
            variable=variable,
            depth_idx=depth_idx,
            time_idx=time_idx,
            lon_min=lon_min,
            lon_max=lon_max,
            lat_min=lat_min,
            lat_max=lat_max,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/currents/{dataset_id}", response_model=CurrentField)
def get_currents(
    dataset_id: str,
    depth_idx: int = Query(0, ge=0),
    time_idx: int = Query(0, ge=0),
    lon_min: float = Query(40.0),
    lon_max: float = Query(100.0),
    lat_min: float = Query(-30.0),
    lat_max: float = Query(30.0),
):
    """Return u/v current vector field."""
    try:
        return dataset_service.get_current_field(
            dataset_id=dataset_id,
            depth_idx=depth_idx,
            time_idx=time_idx,
            lon_min=lon_min,
            lon_max=lon_max,
            lat_min=lat_min,
            lat_max=lat_max,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/model-profile/{dataset_id}")
def get_model_profile(
    dataset_id: str,
    variable: str = Query("thetao"),
    lat: float = Query(...),
    lon: float = Query(...),
    time_idx: int = Query(0),
):
    """Return a vertical model profile at nearest grid point."""
    try:
        return dataset_service.get_model_profile(
            dataset_id=dataset_id,
            variable=variable,
            lat=lat,
            lon=lon,
            time_idx=time_idx,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
