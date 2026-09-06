# API Documentation — SAGAR-VIEW

Base URL: `http://localhost:8000`

Interactive docs: http://localhost:8000/docs

---

## Endpoints

### GET `/api/datasets`
Returns all available datasets.

**Response**: `DatasetInfo[]`
```json
[{
  "id": "indian_ocean_demo",
  "name": "Indian Ocean Demo — SAGAR-VIEW",
  "source": "demo",
  "lon_min": 40.0, "lon_max": 100.0,
  "lat_min": -30.0, "lat_max": 30.0,
  "depth_levels": [5, 10, 15, ...],
  "time_steps": ["2023-01-01", ...],
  "variables": [{"name": "thetao", "units": "°C", ...}],
  "resolution_deg": 0.25
}]
```

---

### GET `/api/fields/{dataset_id}`
Returns a 2D ocean field at a specific depth and time.

**Query params**:
| Param | Default | Description |
|-------|---------|-------------|
| `variable` | `thetao` | Variable name |
| `depth_idx` | `0` | Depth level index |
| `time_idx` | `0` | Time step index |
| `lon_min/max` | `40/100` | Bounding box |
| `lat_min/max` | `-30/30` | Bounding box |

**Response**: `OceanField`
```json
{
  "variable": "thetao", "units": "°C",
  "depth_m": 5.0, "time_step": "2023-01-01",
  "n_lon": 241, "n_lat": 241,
  "values": [28.1, 27.9, null, ...],
  "vmin": 5.2, "vmax": 31.4,
  "colormap_hint": "thermal"
}
```

---

### GET `/api/currents/{dataset_id}`
Returns u/v current vector field.

**Query params**: same as `/api/fields`

**Response**: `CurrentField`
```json
{
  "u_values": [0.12, -0.05, ...],
  "v_values": [0.08, 0.22, ...],
  "speed_max": 1.34
}
```

---

### GET `/api/model-profile/{dataset_id}`
Vertical profile at nearest grid point.

**Query params**: `variable`, `lat`, `lon`, `time_idx`

**Response**: `[{"depth": 5.0, "value": 28.1}, ...]`

---

### GET `/api/observations`
Returns Argo float platforms in bounding box.

**Query params**: `lon_min`, `lon_max`, `lat_min`, `lat_max`, `date_start`, `date_end`, `max_platforms`

**Response**: `ObservationPlatform[]`

---

### GET `/api/profiles/{platform_id}`
Returns full depth profile for a platform.

**Response**: `OceanProfile`
```json
{
  "platform_id": "ARGO_6900000",
  "latitude": 12.3, "longitude": 68.7,
  "levels": [
    {"depth": 5, "temperature": 28.1, "salinity": 34.9},
    ...
  ]
}
```

---

### GET `/api/profiles/{platform_id}/collocate`
Model-observation collocation at platform location.

**Query params**: `dataset_id`, `variable`, `time_idx`

**Response**: `CollocateResult`
```json
{
  "levels": [
    {"depth": 5, "model_value": 28.3, "obs_value": 28.1, "difference": 0.2},
    ...
  ],
  "mean_absolute_difference": 0.342,
  "n_matched": 18,
  "note": "Simple nearest-grid-point collocation..."
}
```

---

### GET `/api/export/field`
Download a field slice as JSON or CSV.

**Query params**: `dataset_id`, `variable`, `depth_idx`, `time_idx`, `format`

---

### GET `/api/export/profile/{platform_id}`
Download a profile as JSON or CSV.

**Query params**: `format`

---

### GET `/health`
```json
{"status": "ok", "cache": {"memory": {...}, "redis": false}, "demo_mode": true}
```
