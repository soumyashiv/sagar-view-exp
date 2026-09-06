# SAGAR-VIEW

> SIH 2026 · Problem Statement 26067

An interactive 3D ocean visualization platform for the Indian Ocean.

## Start

```bash
# One-click launch (Windows):
start.bat

# Or manually:
cd backend && python scripts/generate_demo_data.py
cd backend && python -m uvicorn app.main:app --reload
cd frontend && npm run dev
```

- **Frontend**: http://localhost:3000
- **API docs**: http://localhost:8000/docs

## Full Documentation

See [docs/README.md](docs/README.md) for complete setup, architecture, and API reference.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Three.js, Tailwind CSS |
| State | Zustand, TanStack React Query |
| Backend | FastAPI, Python, xarray, NetCDF4 |
| Caching | In-memory LRU (Redis optional) |
| Data | Synthetic Indian Ocean NetCDF + Argovis API |
