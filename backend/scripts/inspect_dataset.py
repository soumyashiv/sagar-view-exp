#!/usr/bin/env python3
"""
Inspect a NetCDF dataset and print a summary.

Usage:
  python inspect_dataset.py path/to/file.nc
  python inspect_dataset.py path/to/file.nc --json
"""
import sys
import json
import argparse
from pathlib import Path


def inspect(path: Path, as_json: bool = False) -> dict:
    try:
        import xarray as xr
    except ImportError:
        print("ERROR: xarray not installed.")
        sys.exit(1)

    ds = xr.open_dataset(path, engine="netcdf4")

    summary = {
        "file": str(path),
        "size_mb": round(path.stat().st_size / 1e6, 2),
        "dimensions": {k: v for k, v in ds.dims.items()},
        "coordinates": {},
        "variables": {},
        "global_attrs": {k: str(getattr(ds, k)) for k in ds.attrs},
    }

    for coord in ds.coords:
        arr = ds[coord].values
        try:
            summary["coordinates"][coord] = {
                "dtype": str(arr.dtype),
                "shape": list(arr.shape),
                "min": float(arr.min()),
                "max": float(arr.max()),
                "units": str(ds[coord].attrs.get("units", "")),
            }
        except Exception:
            pass

    for var in ds.data_vars:
        da = ds[var]
        summary["variables"][var] = {
            "dims": list(da.dims),
            "shape": list(da.shape),
            "dtype": str(da.dtype),
            "units": str(da.attrs.get("units", "")),
            "long_name": str(da.attrs.get("long_name", "")),
            "standard_name": str(da.attrs.get("standard_name", "")),
        }

    ds.close()

    if as_json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"File: {summary['file']}  ({summary['size_mb']} MB)")
        print(f"Dimensions: {summary['dimensions']}")
        print(f"\nCoordinates:")
        for name, info in summary["coordinates"].items():
            print(f"  {name}: shape={info['shape']}  range=[{info['min']:.3f}, {info['max']:.3f}]  units={info['units']}")
        print(f"\nData Variables:")
        for name, info in summary["variables"].items():
            print(f"  {name}: dims={info['dims']}  shape={info['shape']}  units={info['units']}")
            if info['long_name']:
                print(f"          long_name='{info['long_name']}'")
        print(f"\nGlobal Attrs: {list(summary['global_attrs'].keys())}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect a NetCDF dataset")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if not args.path.exists():
        print(f"ERROR: File not found: {args.path}")
        sys.exit(1)

    inspect(args.path, args.as_json)
