"""Portfolio Mode (section 28), scoped for this build to CSV upload.

GeoJSON/Shapefile/GeoPackage/KML ingestion is documented as a near-term
follow-up in docs/KNOWN_LIMITATIONS.md - CSV covers the common
insurance/utility exposure-list workflow and lets us implement real
validation and exposure logic rather than a stub for every format.
"""

from __future__ import annotations

import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import ValidationError

from app.api.deps import repo_dep
from app.db.memory_repository import MemoryRepository
from app.schemas.portfolio import PortfolioAsset, PortfolioExposure, PortfolioValidationIssue
from app.services.geo import point_in_polygon

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB upload-size limit (section 40)
MAX_ROWS = 20_000


@router.post("/upload", response_model=PortfolioExposure)
async def upload_portfolio(
    file: UploadFile, repo: MemoryRepository = Depends(repo_dep)
) -> PortfolioExposure:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv is supported in this build.")

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 5 MB upload limit.")

    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    assets: list[PortfolioAsset] = []
    issues: list[PortfolioValidationIssue] = []
    seen_ids: set[str] = set()

    for i, row in enumerate(reader, start=2):  # header is row 1
        if i - 1 > MAX_ROWS:
            issues.append(PortfolioValidationIssue(issue=f"Row limit of {MAX_ROWS} exceeded; truncating."))
            break
        asset_id = (row.get("asset_id") or "").strip()
        if not asset_id:
            issues.append(PortfolioValidationIssue(row_number=i, field="asset_id", issue="Missing asset_id."))
            continue
        if asset_id in seen_ids:
            issues.append(PortfolioValidationIssue(row_number=i, field="asset_id", issue=f"Duplicate asset_id '{asset_id}'."))
            continue
        seen_ids.add(asset_id)

        try:
            lat = float(row.get("lat", ""))
            lon = float(row.get("lon", ""))
        except (TypeError, ValueError):
            issues.append(PortfolioValidationIssue(row_number=i, field="lat/lon", issue="Missing or non-numeric coordinates."))
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            issues.append(PortfolioValidationIssue(row_number=i, field="lat/lon", issue="Coordinates out of valid range."))
            continue

        value_raw = row.get("replacement_value_usd")
        try:
            value = float(value_raw) if value_raw not in (None, "") else None
        except ValueError:
            issues.append(PortfolioValidationIssue(row_number=i, field="replacement_value_usd", issue="Non-numeric replacement value."))
            value = None

        try:
            assets.append(
                PortfolioAsset(
                    row_number=i,
                    asset_id=asset_id,
                    name=row.get("name"),
                    lat=lat,
                    lon=lon,
                    asset_type=row.get("asset_type"),
                    replacement_value_usd=value,
                )
            )
        except ValidationError as exc:
            issues.append(PortfolioValidationIssue(row_number=i, issue=str(exc)))

    alerts = repo.list_alerts(mode="live")
    warning_rings = alerts[0].geometry.coordinates if alerts and alerts[0].geometry.type == "Polygon" else []
    in_alert = sum(1 for a in assets if point_in_polygon((a.lon, a.lat), warning_rings))
    missing_value = sum(1 for a in assets if a.replacement_value_usd is None)

    portfolio_id = f"pf-{uuid.uuid4().hex[:10]}"
    repo.save_portfolio(portfolio_id, {"assets": [a.model_dump() for a in assets]})

    return PortfolioExposure(
        portfolio_id=portfolio_id,
        asset_count=len(assets) + sum(1 for iss in issues if iss.row_number),
        valid_asset_count=len(assets),
        assets_in_active_alert=in_alert,
        accumulation_hotspot_note=(
            f"{in_alert} of {len(assets)} valid assets fall inside the current active alert area."
            if assets
            else "No valid assets to assess."
        ),
        missing_value_count=missing_value,
        validation_issues=issues,
    )


@router.get("/{portfolio_id}/exposure", response_model=PortfolioExposure)
def get_portfolio_exposure(
    portfolio_id: str, repo: MemoryRepository = Depends(repo_dep)
) -> PortfolioExposure:
    stored = repo.get_portfolio(portfolio_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Portfolio not found. Upload a CSV first.")
    assets = [PortfolioAsset(**a) for a in stored["assets"]]
    alerts = repo.list_alerts(mode="live")
    warning_rings = alerts[0].geometry.coordinates if alerts and alerts[0].geometry.type == "Polygon" else []
    in_alert = sum(1 for a in assets if point_in_polygon((a.lon, a.lat), warning_rings))
    missing_value = sum(1 for a in assets if a.replacement_value_usd is None)
    return PortfolioExposure(
        portfolio_id=portfolio_id,
        asset_count=len(assets),
        valid_asset_count=len(assets),
        assets_in_active_alert=in_alert,
        accumulation_hotspot_note=f"{in_alert} of {len(assets)} valid assets fall inside the current active alert area.",
        missing_value_count=missing_value,
        validation_issues=[],
    )
