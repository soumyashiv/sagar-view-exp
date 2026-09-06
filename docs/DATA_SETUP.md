# Data Setup Guide — SAGAR-VIEW

## Step 1 — Generate Demo Data (Required for MVP)

The demo dataset is synthetic but physics-inspired. It works offline.

```bash
cd backend
python scripts/generate_demo_data.py
```

This creates `backend/data/demo/indian_ocean_demo.nc` (~45 MB).

Inspect it:
```bash
python scripts/inspect_dataset.py data/demo/indian_ocean_demo.nc
```

Validate it:
```bash
python scripts/validate_netcdf.py data/demo/indian_ocean_demo.nc
```

---

## Step 2 — Real CMEMS Data (Optional)

### Requirements
- Free account at https://marine.copernicus.eu
- `pip install copernicusmarine`
- Run `copernicusmarine login`

### Download Indian Ocean subset
```python
import copernicusmarine

copernicusmarine.subset(
    dataset_id="cmems_mod_glo_phy_my_0.083_P1D-m",
    variables=["thetao", "so", "uo", "vo", "zos"],
    start_datetime="2023-01-01T00:00:00",
    end_datetime="2023-12-31T00:00:00",
    minimum_longitude=40,
    maximum_longitude=100,
    minimum_latitude=-30,
    maximum_latitude=30,
    minimum_depth=0,
    maximum_depth=2000,
    output_filename="backend/data/demo/indian_ocean_demo.nc",
    force_download=True,
)
```

Set `DEMO_NC_FILENAME=indian_ocean_demo.nc` in `.env`.

---

## Step 3 — Real INCOIS Data (Optional)

INCOIS exposes data via THREDDS/OPeNDAP and ERDDAP:
- ERDDAP: https://erddap.incois.gov.in
- THREDDS: https://thredds.incois.gov.in

Access via xarray:
```python
import xarray as xr

ds = xr.open_dataset(
    "https://thredds.incois.gov.in/thredds/dodsC/INCOIS_SST_Daily.nc",
    engine="pydap",
)
```

Implement the `INCOISAdapter` by extending `BaseAdapter`.

---

## Step 4 — Live Argo Data

By default, SAGAR-VIEW calls the **Argovis API** (no auth required):
```
https://argovis.colorado.edu/argo?polygon=...
```

To switch to `argopy`:
1. `pip install argopy`
2. Set `DEMO_MODE=false` in `.env`

The `ArgoAdapter` in `backend/app/adapters/argo_adapter.py` implements this.

---

## Caching

### In-memory (default)
Works out of the box. LRU with 256 entries, 5-minute TTL.

### Redis (optional)
```bash
# Install Redis (WSL2 on Windows recommended)
wsl sudo apt install redis-server && redis-server

# Set in backend/.env
REDIS_URL=redis://localhost:6379
```

---

## Environment Variables

Create `backend/.env`:
```env
DEMO_MODE=true
DEMO_NC_FILENAME=indian_ocean_demo.nc
REDIS_URL=               # leave empty for in-memory
ARGOVIS_API_KEY=         # optional
```

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```
