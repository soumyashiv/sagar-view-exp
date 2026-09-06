"""Pydantic response models for SAGAR-VIEW API."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


# ── Dataset catalogue ────────────────────────────────────────────────────────

class VariableMeta(BaseModel):
    name: str
    long_name: str
    units: str
    standard_name: str
    colormap_hint: str  # e.g. "thermal", "haline", "speed"


class DatasetInfo(BaseModel):
    id: str
    name: str
    source: str          # "demo" | "cmems" | "incois"
    description: str
    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float
    depth_levels: list[float]
    time_steps: list[str]   # ISO strings
    variables: list[VariableMeta]
    resolution_deg: float


# ── Ocean field payload ───────────────────────────────────────────────────────

class OceanField(BaseModel):
    dataset_id: str
    variable: str
    units: str
    depth_m: float
    time_step: str          # ISO
    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float
    n_lon: int
    n_lat: int
    values: list[float]     # flattened row-major [lat0,lon0..lonN, lat1,...] NaN for land
    vmin: float
    vmax: float
    colormap_hint: str


class CurrentField(BaseModel):
    dataset_id: str
    depth_m: float
    time_step: str
    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float
    n_lon: int
    n_lat: int
    u_values: list[float]
    v_values: list[float]
    speed_max: float


# ── Observation models ────────────────────────────────────────────────────────

class ObservationPlatform(BaseModel):
    platform_id: str
    platform_type: str      # "argo" | "glider" | "ctd"
    latitude: float
    longitude: float
    timestamp: str          # ISO
    depth_min: float
    depth_max: float
    variables: list[str]
    wmo: Optional[str] = None
    cycle_number: Optional[int] = None


class ProfileLevel(BaseModel):
    depth: float
    temperature: Optional[float] = None
    salinity: Optional[float] = None
    oxygen: Optional[float] = None
    pressure: Optional[float] = None


class OceanProfile(BaseModel):
    platform_id: str
    platform_type: str
    latitude: float
    longitude: float
    timestamp: str
    levels: list[ProfileLevel]
    variables: list[str]
    metadata: dict


# ── Collocation / comparison ──────────────────────────────────────────────────

class CollocateLevel(BaseModel):
    model_config = {"protected_namespaces": ()}
    depth: float
    model_value: Optional[float]
    obs_value: Optional[float]
    difference: Optional[float]


class CollocateResult(BaseModel):
    model_config = {"protected_namespaces": ()}
    platform_id: str
    variable: str
    units: str
    latitude: float
    longitude: float
    timestamp: str
    levels: list[CollocateLevel]
    mean_absolute_difference: float
    n_matched: int
    note: str


# ── Export ───────────────────────────────────────────────────────────────────

class ExportResponse(BaseModel):
    format: str
    filename: str
    download_url: str
    size_bytes: int
