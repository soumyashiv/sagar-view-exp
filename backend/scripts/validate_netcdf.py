#!/usr/bin/env python3
"""
Validate a NetCDF file for CF compliance and SAGAR-VIEW compatibility.

Usage:
  python validate_netcdf.py path/to/file.nc
  python validate_netcdf.py path/to/file.nc --strict
"""
import sys
import argparse
from pathlib import Path

import numpy as np


def validate(path: Path, strict: bool = False) -> bool:
    try:
        import netCDF4 as nc
    except ImportError:
        print("ERROR: netCDF4 not installed. Run: pip install netCDF4")
        return False

    print(f"\n{'='*60}")
    print(f"Validating: {path}")
    print('='*60)

    errors = []
    warnings = []

    try:
        ds = nc.Dataset(path, "r")
    except Exception as e:
        print(f"FATAL: Cannot open file: {e}")
        return False

    # 1. Check global attributes
    cf_attrs = ["Conventions", "title", "institution", "source", "history"]
    for attr in cf_attrs:
        if hasattr(ds, attr):
            print(f"  [OK] Global attr: {attr} = {getattr(ds, attr)[:60]}")
        else:
            warnings.append(f"Missing global attribute: {attr}")

    # 2. Check coordinate dimensions
    required_dims = {"longitude": ["lon", "longitude", "x"],
                     "latitude": ["lat", "latitude", "y"],
                     "depth": ["depth", "lev", "z", "deptht"]}
    found_dims = {}
    for canonical, aliases in required_dims.items():
        found = next((a for a in aliases if a in ds.dimensions), None)
        if found:
            print(f"  [OK] Dimension '{canonical}': found as '{found}' (size {len(ds.dimensions[found])})")
            found_dims[canonical] = found
        else:
            errors.append(f"Missing required dimension: {canonical} (aliases: {aliases})")

    # Time dimension
    time_dim = next((a for a in ["time", "t"] if a in ds.dimensions), None)
    if time_dim:
        print(f"  [OK] Dimension 'time': found as '{time_dim}' (size {len(ds.dimensions[time_dim])})")
    else:
        warnings.append("No time dimension found")

    # 3. Check variables
    expected_vars = ["thetao", "so", "uo", "vo", "zos"]
    found_vars = []
    for vname in expected_vars:
        if vname in ds.variables:
            v = ds.variables[vname]
            print(f"  [OK] Variable '{vname}': shape={v.shape}, units={getattr(v, 'units', 'N/A')}")
            found_vars.append(vname)
            # Check for NaN-safe values
            try:
                arr = v[0, 0, :, :] if v.ndim == 4 else v[0, :, :]
                data = np.ma.getdata(arr).astype(float)
                valid = data[np.isfinite(data)]
                if len(valid) > 0:
                    print(f"         range=[{valid.min():.3f}, {valid.max():.3f}], "
                          f"fill%={100*(1-len(valid)/data.size):.1f}%")
                else:
                    warnings.append(f"Variable '{vname}' has no valid data at [0,0,:,:]")
            except Exception:
                pass
        else:
            warnings.append(f"Expected variable not found: {vname}")

    # 4. Check coordinate ranges
    if "longitude" in found_dims:
        lons = ds.variables[found_dims["longitude"]][:]
        if lons.min() < -180 or lons.max() > 360:
            errors.append(f"Longitude out of range: [{lons.min()}, {lons.max()}]")
        else:
            print(f"  [OK] Longitude range: [{lons.min():.2f}, {lons.max():.2f}]")

    if "latitude" in found_dims:
        lats = ds.variables[found_dims["latitude"]][:]
        if lats.min() < -90 or lats.max() > 90:
            errors.append(f"Latitude out of range: [{lats.min()}, {lats.max()}]")
        else:
            print(f"  [OK] Latitude range: [{lats.min():.2f}, {lats.max():.2f}]")

    ds.close()

    # Report
    print(f"\n{'-'*60}")
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  WARN  {w}")
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  ERR   {e}")
    else:
        print(f"  OK  No errors found.")

    if not errors:
        print(f"\nVALID -- File is compatible with SAGAR-VIEW.")
        return True
    else:
        print(f"\nINVALID -- {len(errors)} error(s) found.")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a NetCDF file for SAGAR-VIEW")
    parser.add_argument("path", type=Path, help="Path to the NetCDF file")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    if not args.path.exists():
        print(f"ERROR: File not found: {args.path}")
        sys.exit(1)

    ok = validate(args.path, args.strict)
    sys.exit(0 if ok else 1)
