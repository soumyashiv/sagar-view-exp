"""Tests for NetCDF parsing and dataset service."""
import sys
from pathlib import Path
import pytest
import numpy as np

# Make sure backend package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_demo_file_exists_after_generation(tmp_path):
    """Generate demo data to tmp_path and verify it can be parsed."""
    import netCDF4 as nc

    # Import and run generator against tmp_path
    from scripts.generate_demo_data import generate, OUT_PATH as ORIG_OUT_PATH
    import scripts.generate_demo_data as gen_mod

    out = tmp_path / "test_demo.nc"
    original = gen_mod.OUT_PATH
    gen_mod.OUT_PATH = out
    try:
        generate()
    finally:
        gen_mod.OUT_PATH = original

    assert out.exists(), "NetCDF file was not created"
    assert out.stat().st_size > 1000, "NetCDF file is suspiciously small"

    ds = nc.Dataset(out, "r")
    assert "longitude" in ds.dimensions
    assert "latitude" in ds.dimensions
    assert "depth" in ds.dimensions
    assert "time" in ds.dimensions
    ds.close()


def test_demo_variables_present(tmp_path):
    """All required variables must exist in the generated NetCDF."""
    import netCDF4 as nc
    import scripts.generate_demo_data as gen_mod

    out = tmp_path / "vars_demo.nc"
    gen_mod.OUT_PATH = out
    gen_mod.generate()

    ds = nc.Dataset(out, "r")
    for var in ["thetao", "so", "uo", "vo", "zos"]:
        assert var in ds.variables, f"Variable '{var}' missing from NetCDF"
    ds.close()


def test_temperature_range(tmp_path):
    """Temperature values must be within physical bounds."""
    import netCDF4 as nc
    import scripts.generate_demo_data as gen_mod

    out = tmp_path / "T_demo.nc"
    gen_mod.OUT_PATH = out
    gen_mod.generate()

    ds = nc.Dataset(out, "r")
    T = ds.variables["thetao"][0, 0, :, :]  # first time, surface
    valid = T[~np.isnan(T.data)]
    assert valid.min() >= 0.0, "Temperature too cold at surface"
    assert valid.max() <= 35.0, "Temperature too warm at surface"
    ds.close()


def test_salinity_range(tmp_path):
    """Salinity values must be within physical bounds."""
    import netCDF4 as nc
    import scripts.generate_demo_data as gen_mod

    out = tmp_path / "S_demo.nc"
    gen_mod.OUT_PATH = out
    gen_mod.generate()

    ds = nc.Dataset(out, "r")
    S = ds.variables["so"][0, 0, :, :]
    valid = S[~np.isnan(S.data)]
    assert valid.min() >= 25.0
    assert valid.max() <= 40.0
    ds.close()


def test_coordinate_monotonicity(tmp_path):
    """Coordinates must be strictly monotonic."""
    import netCDF4 as nc
    import scripts.generate_demo_data as gen_mod

    out = tmp_path / "mono_demo.nc"
    gen_mod.OUT_PATH = out
    gen_mod.generate()

    ds = nc.Dataset(out, "r")
    lons = ds.variables["longitude"][:]
    lats = ds.variables["latitude"][:]
    deps = ds.variables["depth"][:]

    assert np.all(np.diff(lons) > 0), "Longitude not monotonically increasing"
    assert np.all(np.diff(lats) > 0), "Latitude not monotonically increasing"
    assert np.all(np.diff(deps) > 0), "Depth not monotonically increasing"
    ds.close()


def test_cf_global_attributes(tmp_path):
    """CF-required global attributes must be present."""
    import netCDF4 as nc
    import scripts.generate_demo_data as gen_mod

    out = tmp_path / "cf_demo.nc"
    gen_mod.OUT_PATH = out
    gen_mod.generate()

    ds = nc.Dataset(out, "r")
    assert hasattr(ds, "Conventions")
    assert "CF" in ds.Conventions
    assert hasattr(ds, "title")
    assert hasattr(ds, "institution")
    ds.close()
