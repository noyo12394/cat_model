"""Portfolio Mode schemas (section 28) - scoped to CSV upload for this build."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PortfolioAsset(BaseModel):
    row_number: int
    asset_id: str
    name: str | None = None
    lat: float
    lon: float
    asset_type: str | None = None
    replacement_value_usd: float | None = None


class PortfolioValidationIssue(BaseModel):
    row_number: int | None = None
    field: str | None = None
    issue: str


class PortfolioExposure(BaseModel):
    portfolio_id: str
    asset_count: int
    valid_asset_count: int
    assets_in_active_alert: int
    accumulation_hotspot_note: str
    missing_value_count: int
    validation_issues: list[PortfolioValidationIssue] = Field(default_factory=list)
    disclaimer: str = (
        "Uploaded asset data is processed for this session only in this build and is never "
        "exposed to other users; see docs/SECURITY.md for the production tenant-isolation plan."
    )
