"""Tests for model-observation collocation service."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.schemas import OceanProfile, ProfileLevel
from app.services import collocate_service


def _make_profile(lat=10.0, lon=65.0) -> OceanProfile:
    depths = [5, 10, 20, 50, 100, 200, 500]
    levels = []
    for d in depths:
        T = 28 - d * 0.02
        S = 35.0 + d * 0.001
        levels.append(ProfileLevel(depth=float(d), temperature=T, salinity=S, pressure=float(d)))

    return OceanProfile(
        platform_id="TEST_001",
        platform_type="argo",
        latitude=lat,
        longitude=lon,
        timestamp="2023-06-01T00:00:00Z",
        levels=levels,
        variables=["temperature", "salinity"],
        metadata={},
    )


def test_collocate_interpolation():
    """Test that linear interpolation gives sensible results."""
    from app.services.collocate_service import _interpolate_profile

    profile = {0.0: 28.0, 100.0: 20.0, 500.0: 8.0}
    depths = [0.0, 100.0, 500.0]

    # Exact match
    assert _interpolate_profile(profile, depths, 0.0) == 28.0
    assert _interpolate_profile(profile, depths, 100.0) == 20.0

    # Interpolated midpoint
    v = _interpolate_profile(profile, depths, 50.0)
    assert v is not None
    assert 20.0 < v < 28.0

    # Extrapolation: below deepest
    v_deep = _interpolate_profile(profile, depths, 1000.0)
    assert v_deep == 8.0

    # Extrapolation: above shallowest
    v_shallow = _interpolate_profile(profile, depths, -5.0)
    assert v_shallow == 28.0


def test_collocate_returns_result_structure():
    """CollocateResult should have correct structure."""
    profile = _make_profile()

    # Without demo NetCDF, model profile extraction fails gracefully
    # so collocate should still return a result (with model_value=None)
    try:
        result = collocate_service.collocate(
            dataset_id="indian_ocean_demo",
            variable="thetao",
            profile=profile,
            time_idx=0,
        )
        assert result.platform_id == "TEST_001"
        assert result.variable == "thetao"
        assert isinstance(result.levels, list)
        assert isinstance(result.mean_absolute_difference, float)
        assert result.mean_absolute_difference >= 0.0
        assert "n_matched" in result.model_dump()
    except FileNotFoundError:
        pytest.skip("Demo NetCDF not generated yet — run generate_demo_data.py")


def test_collocate_mad_is_non_negative():
    """MAD must always be non-negative."""
    profile = _make_profile()
    try:
        result = collocate_service.collocate("indian_ocean_demo", "thetao", profile)
        assert result.mean_absolute_difference >= 0.0
    except FileNotFoundError:
        pytest.skip("Demo NetCDF not generated")


def test_collocate_levels_have_depth():
    """Every CollocateLevel must have a depth value."""
    profile = _make_profile()
    try:
        result = collocate_service.collocate("indian_ocean_demo", "thetao", profile)
        for level in result.levels:
            assert level.depth is not None
            assert level.depth >= 0
    except FileNotFoundError:
        pytest.skip("Demo NetCDF not generated")
