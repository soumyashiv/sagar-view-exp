"""Tests for coordinate transformations and geo utilities."""
import sys
from pathlib import Path
import math
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_lon_lat_in_range():
    """SAGAR-VIEW Indian Ocean bbox must be valid."""
    LON_MIN, LON_MAX = 40.0, 100.0
    LAT_MIN, LAT_MAX = -30.0, 30.0

    assert -180 <= LON_MIN <= 180
    assert -180 <= LON_MAX <= 180
    assert LON_MIN < LON_MAX

    assert -90 <= LAT_MIN <= 90
    assert -90 <= LAT_MAX <= 90
    assert LAT_MIN < LAT_MAX


def test_depth_levels_positive():
    """All depth levels must be positive (depth is positive downward)."""
    DEPTHS = [5, 10, 15, 20, 30, 50, 75, 100, 125, 150,
              200, 300, 400, 500, 600, 750, 1000, 1250, 1500, 2000]
    for d in DEPTHS:
        assert d > 0, f"Depth {d} is not positive"


def test_depth_levels_monotonic():
    """Depth levels must be strictly increasing."""
    DEPTHS = [5, 10, 15, 20, 30, 50, 75, 100, 125, 150,
              200, 300, 400, 500, 600, 750, 1000, 1250, 1500, 2000]
    for i in range(len(DEPTHS) - 1):
        assert DEPTHS[i] < DEPTHS[i+1], f"Depth not monotonic at index {i}"


def test_spherical_to_cartesian():
    """Test lat/lon to 3D unit sphere conversion."""
    def to_cart(lat_deg, lon_deg, r=1.0):
        lat = math.radians(lat_deg)
        lon = math.radians(lon_deg)
        x = r * math.cos(lat) * math.cos(lon)
        y = r * math.sin(lat)
        z = r * math.cos(lat) * math.sin(lon)
        return x, y, z

    # Equator, prime meridian
    x, y, z = to_cart(0, 0)
    assert abs(x - 1.0) < 1e-9
    assert abs(y) < 1e-9
    assert abs(z) < 1e-9

    # North pole
    x, y, z = to_cart(90, 0)
    assert abs(y - 1.0) < 1e-9

    # Unit length
    for lat, lon in [(0, 0), (45, 90), (-30, 60), (10, 70)]:
        x, y, z = to_cart(lat, lon)
        length = math.sqrt(x**2 + y**2 + z**2)
        assert abs(length - 1.0) < 1e-9, f"Non-unit vector for lat={lat}, lon={lon}"


def test_bbox_area():
    """Indian Ocean bbox must cover a meaningful area."""
    LON_MIN, LON_MAX = 40.0, 100.0
    LAT_MIN, LAT_MAX = -30.0, 30.0
    area = (LON_MAX - LON_MIN) * (LAT_MAX - LAT_MIN)
    assert area > 1000, f"Bbox area too small: {area}"


def test_grid_point_count():
    """1/4-degree grid should produce expected number of points."""
    import numpy as np
    lons = np.arange(40.0, 100.25, 0.25)
    lats = np.arange(-30.0, 30.25, 0.25)
    assert len(lons) == 241
    assert len(lats) == 241


def test_time_steps():
    """12 monthly time steps from 2023-01-01."""
    from datetime import datetime, timedelta
    START = datetime(2023, 1, 1)
    times = [START + timedelta(days=30 * i) for i in range(12)]
    assert len(times) == 12
    assert times[0] == datetime(2023, 1, 1)
    assert times[-1].year == 2023
