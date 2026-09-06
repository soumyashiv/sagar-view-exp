"""Export router — JSON, CSV, and summary data exports."""
from __future__ import annotations
import json
import csv
import io
import time
from fastapi import APIRouter, Query, Response
from app.services import dataset_service, argo_service

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/field")
async def export_field(
    dataset_id: str = Query("indian_ocean_demo"),
    variable: str = Query("thetao"),
    depth_idx: int = Query(0),
    time_idx: int = Query(0),
    format: str = Query("json", pattern="^(json|csv)$"),
):
    """Export the current ocean field slice as JSON or CSV."""
    field = dataset_service.get_ocean_field(
        dataset_id=dataset_id,
        variable=variable,
        depth_idx=depth_idx,
        time_idx=time_idx,
    )

    if format == "json":
        content = field.model_dump_json(indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{variable}_{depth_idx}_{time_idx}.json"'
            },
        )
    else:
        # Build CSV: lon, lat, value
        import numpy as np
        lons = [round(field.lon_min + i * (field.lon_max - field.lon_min) / max(field.n_lon - 1, 1), 4)
                for i in range(field.n_lon)]
        lats = [round(field.lat_min + j * (field.lat_max - field.lat_min) / max(field.n_lat - 1, 1), 4)
                for j in range(field.n_lat)]

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["longitude", "latitude", variable, "depth_m", "time_step"])
        for j, lat in enumerate(lats):
            for i, lon in enumerate(lons):
                val = field.values[j * field.n_lon + i]
                writer.writerow([lon, lat, val, field.depth_m, field.time_step])

        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{variable}_{depth_idx}_{time_idx}.csv"'
            },
        )


@router.get("/profile/{platform_id}")
async def export_profile(
    platform_id: str,
    format: str = Query("json", pattern="^(json|csv)$"),
):
    """Export an observation profile."""
    profile = await argo_service.get_profile(platform_id)
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Platform not found")

    if format == "json":
        return Response(
            content=profile.model_dump_json(indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="profile_{platform_id}.json"'},
        )
    else:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["platform_id", "latitude", "longitude", "timestamp",
                          "depth", "temperature", "salinity", "pressure"])
        for lvl in profile.levels:
            writer.writerow([
                platform_id, profile.latitude, profile.longitude, profile.timestamp,
                lvl.depth, lvl.temperature, lvl.salinity, lvl.pressure,
            ])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="profile_{platform_id}.csv"'},
        )
