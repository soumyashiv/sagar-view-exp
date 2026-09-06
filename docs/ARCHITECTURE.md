# Rendering Architecture — SAGAR-VIEW

## Overview

The rendering pipeline converts raw NetCDF model data into interactive WebGL visualizations without ever sending bulk data to the browser.

## Data Flow

```
NetCDF file (disk)
    │
    ▼
xarray.open_dataset()          — lazy load, only metadata in RAM
    │
    ▼
Spatial subset                 — sel(lat/lon bbox)
    │
    ▼
Depth/time indexing            — isel(depth_idx, time_idx)
    │
    ▼
numpy array (n_lat × n_lon)    — ~58 KB for 241×241 float32
    │
    ▼
JSON serialization             — nulls for masked/land values
    │
    ▼
HTTP response (~200–500 KB)    — browser receives this only
    │
    ▼
Float32Array (client)          — normalized to [0,1]
    │
    ▼
THREE.DataTexture (GPU)        — n_lon × n_lat texture upload
    │
    ▼
GLSL fragment shader           — samples field + 1D colormap LUT
    │
    ▼
Screen pixels                  — 60 FPS orbit controls
```

## Globe Geometry

- **Earth base**: SphereGeometry(1, 128, 128) with Phong material + earth texture
- **Ocean overlay**: SphereGeometry(1.002, 128, 128) with custom ShaderMaterial
- **Atmosphere**: SphereGeometry(1.05, 64, 64), BackSide, AdditiveBlending

## Shader Design

The `OceanFieldShader` uses a custom `THREE.ShaderMaterial` with:

- **Uniforms**:
  - `uFieldTexture` — DataTexture (RedFormat, FloatType) holding normalized field values
  - `uColormapTexture` — DataTexture (RGBFormat) holding a 16-stop colormap
  - `uOpacity`, `uVmin`, `uVmax` — dynamic controls
  - `uHasData` — 0 before first load; prevents white flash

- **Vertex shader**: passes UV coordinates, normal, and position to fragment stage

- **Fragment shader**:
  1. Samples `uFieldTexture` at UV → raw normalized value
  2. Checks for -1 sentinel (land/masked) → `discard`
  3. Re-maps using `uVmin/uVmax`
  4. Samples `uColormapTexture` at value → RGB
  5. Applies diffuse lighting term
  6. Outputs `vec4(color, uOpacity)`

## Colormap System

Six colormaps are defined as 16-stop RGB arrays in `src/lib/colormaps.ts`:
- **Thermal** — cold blue → warm orange/yellow (temperature)
- **Haline** — purple → blue → green → yellow (salinity)
- **Speed** — white → dark green → black (velocity magnitude)
- **Balance** — blue → white → red (diverging, SSH)
- **Viridis** — purple → cyan → yellow
- **Jet** — blue → cyan → green → yellow → red

Each is built into a `Uint8Array` and uploaded as a `THREE.DataTexture` (16×1 texels, RGB). The fragment shader samples it with `texture2D(uColormapTexture, vec2(t, 0.5))`.

## Current Vector Rendering

Current vectors (uo, vo) are rendered as cone instances:
1. `CurrentField` JSON delivers decimated u/v arrays
2. Every 8th grid point is rendered as a `ConeGeometry`
3. Cone is positioned on the sphere surface and oriented tangentially
4. Size scales linearly with wind/current speed magnitude

## Observation Markers

Argo float markers are `SphereGeometry(0.007)` instances:
- Positioned using `latLonToSphere(lat, lon, 1.015)` (slightly above ocean)
- Raycasted on click to identify the platform
- Selected platform: gold color + ring glow

## Performance Notes

- **Field texture upload**: ~58 KB per frame for 241×241 float32 — negligible
- **Camera**: OrbitControls with damping, min/max distance clamps
- **Pixel ratio**: capped at 2 for HiDPI screens
- **Markers**: ~40 SphereGeometry instances — no batching needed at this scale
- **Arrows**: decimated to every 8th point (~900 cones max)

## Upgrade Paths

| Feature | Current | Upgrade |
|---------|---------|---------|
| Data format | JSON | Binary (Protobuf/MessagePack) |
| Colormap | 16-stop LUT | 256-stop texture |
| Arrows | ConeGeometry instances | InstancedMesh |
| Isosurfaces | Not implemented | Marching cubes on GPU |
| 3D depth | Single slice | Volume ray-casting |
