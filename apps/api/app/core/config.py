"""Application settings.

Every external integration is optional. When a credential is absent, the
corresponding adapter automatically falls back to a typed demo provider and
every response it produces is labeled ``data_status: demo``. This lets the
whole platform run with zero configuration (section 46).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "EarthPulse API"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"

    # CORS
    cors_allow_origins: str = "http://localhost:3000"

    # --- Live data adapters: all optional, mock fallback if unset ---
    nws_base_url: str = "https://api.weather.gov"
    # Modern USGS Water Data OGC API. The legacy waterservices endpoints are
    # scheduled for retirement, so new integrations must not depend on them.
    usgs_water_base_url: str = "https://api.waterdata.usgs.gov/ogcapi/v0"
    usgs_quake_base_url: str = "https://earthquake.usgs.gov/earthquakes/feed/v1.0"
    gdacs_base_url: str = "https://www.gdacs.org/gdacsapi/api"
    firms_map_key: str | None = None  # NASA FIRMS MAP_KEY
    airnow_api_key: str | None = None  # AirNow API key
    openfema_base_url: str = "https://www.fema.gov/api/open"
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    nominatim_user_agent: str = "RiskChain-CAT/0.1 (https://earthpulse-cat-model.vercel.app)"

    # Community reports: read-only X API access. Without an approved Bearer
    # Token, no social data or substitute sentiment is shown in the product.
    x_bearer_token: str | None = None
    x_api_base_url: str = "https://api.x.com/2"

    # --- Google Maps Platform (frontend consumes NEXT_PUBLIC_* directly; the
    # backend only ever needs a server-side key for Routes/Places proxying) ---
    google_maps_server_api_key: str | None = None

    # --- Storage / cache (used when running the full docker-compose stack;
    # the API works with in-memory demo storage when these are unset) ---
    database_url: str | None = None
    redis_url: str | None = None

    # --- AI assistant: the Grounded AI Assistant works fully offline using
    # templated, evidence-grounded responses. A Groq key upgrades prose only;
    # computed hazard facts and numbers never come from the language model. ---
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    rate_limit_per_minute: int = 120

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
