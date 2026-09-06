"""Application configuration via pydantic-settings."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Paths
    data_dir: Path = Path(__file__).parent.parent / "data"
    demo_dir: Path = Path(__file__).parent.parent / "data" / "demo"
    cache_dir: Path = Path(__file__).parent.parent / "data" / "cache"

    # Server
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    debug: bool = True

    # Demo mode (use synthetic data instead of live APIs)
    demo_mode: bool = True
    demo_nc_filename: str = "indian_ocean_demo.nc"

    # Redis (optional — falls back to in-memory if not set)
    redis_url: str | None = None

    # External APIs
    argovis_base_url: str = "https://argovis.colorado.edu"
    argovis_api_key: str | None = None

    # Cache TTL seconds
    field_cache_ttl: int = 300
    obs_cache_ttl: int = 600

    # Indian Ocean bounding box (default subset)
    default_lon_min: float = 40.0
    default_lon_max: float = 100.0
    default_lat_min: float = -30.0
    default_lat_max: float = 30.0


settings = Settings()

# Ensure directories exist
settings.demo_dir.mkdir(parents=True, exist_ok=True)
settings.cache_dir.mkdir(parents=True, exist_ok=True)
