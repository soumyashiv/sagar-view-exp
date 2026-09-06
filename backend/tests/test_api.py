"""API integration tests using FastAPI TestClient."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def demo_nc(tmp_path_factory):
    """Generate demo NetCDF once for all API tests."""
    tmp = tmp_path_factory.mktemp("data")
    out = tmp / "indian_ocean_demo.nc"
    import scripts.generate_demo_data as gen_mod
    original = gen_mod.OUT_PATH
    gen_mod.OUT_PATH = out
    gen_mod.generate()
    gen_mod.OUT_PATH = original
    return out


@pytest.fixture(scope="module")
def client(demo_nc, monkeypatch_module):
    """TestClient with demo data wired in."""
    import app.config as cfg_mod
    monkeypatch_module.setattr(cfg_mod.settings, "demo_dir", demo_nc.parent)
    monkeypatch_module.setattr(cfg_mod.settings, "demo_mode", True)

    from app.main import app as fastapi_app
    return TestClient(fastapi_app)


@pytest.fixture(scope="module")
def monkeypatch_module():
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


# ── Simpler approach: use real demo data if available ─────────────────────────

@pytest.fixture(scope="session")
def simple_client():
    from app.main import app as fastapi_app
    return TestClient(fastapi_app, raise_server_exceptions=False)


def test_root(simple_client):
    resp = simple_client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "SAGAR-VIEW API"


def test_health(simple_client):
    resp = simple_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "cache" in data


def test_datasets_endpoint(simple_client):
    resp = simple_client.get("/api/datasets")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_observations_endpoint(simple_client):
    resp = simple_client.get("/api/observations?lon_min=40&lon_max=100&lat_min=-30&lat_max=30")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # In demo mode we expect ≥10 platforms
    assert len(data) >= 10


def test_observations_bbox_filter(simple_client):
    # Small bbox — fewer platforms
    resp = simple_client.get("/api/observations?lon_min=60&lon_max=70&lat_min=5&lat_max=15")
    assert resp.status_code == 200
    data = resp.json()
    for platform in data:
        assert 60 <= platform["longitude"] <= 70
        assert 5 <= platform["latitude"] <= 15


def test_profile_endpoint(simple_client):
    # Get first platform and fetch its profile
    obs_resp = simple_client.get("/api/observations")
    obs = obs_resp.json()
    if obs:
        pid = obs[0]["platform_id"]
        resp = simple_client.get(f"/api/profiles/{pid}")
        assert resp.status_code == 200
        profile = resp.json()
        assert "levels" in profile
        assert len(profile["levels"]) > 0
        assert "latitude" in profile
        assert "longitude" in profile


def test_profile_has_temperature_and_salinity(simple_client):
    obs_resp = simple_client.get("/api/observations")
    obs = obs_resp.json()
    if obs:
        pid = obs[0]["platform_id"]
        resp = simple_client.get(f"/api/profiles/{pid}")
        profile = resp.json()
        for level in profile["levels"][:5]:
            assert "depth" in level
            assert "temperature" in level or "salinity" in level


def test_404_on_unknown_profile(simple_client):
    resp = simple_client.get("/api/profiles/NONEXISTENT_PLATFORM_XYZ")
    assert resp.status_code == 404


def test_openapi_schema(simple_client):
    resp = simple_client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "paths" in schema
