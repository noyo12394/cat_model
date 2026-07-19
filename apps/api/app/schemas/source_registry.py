"""Typed, client-visible metadata for external source governance."""

from __future__ import annotations

from pydantic import BaseModel


class SourceRegistryRecord(BaseModel):
    key: str
    display_name: str
    organization: str
    requires_key_env: str | None
    docs_url: str
    access_method: str
    license_summary: str
    commercial_use_status: str
    update_frequency: str
    geographic_coverage: str
    spatial_resolution: str
    temporal_resolution: str
    required_attribution: str
    quality_notes: str
    deprecation_status: str
    fallback_source: str | None
    terms_url: str | None
    verified_at: str
