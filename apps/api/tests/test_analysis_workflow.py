from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.api.v1 import analysis
from app.core.config import Settings
from app.schemas.analysis import AnalysisLocation, AnalysisRunRequest, AnalysisTotals, SourceRecord
from app.services.cat.screening import point_in_geometry

LOCATION=AnalysisLocation(place_id="bethlehem-pa",name="Bethlehem, Pennsylvania",center=(-75.3705,40.6259),bbox=(-75.40,40.60,-75.34,40.65),state="Pennsylvania",state_fips="42",county="Lehigh County",county_fips="42077",tract="Census Tract 65",tract_geoid="42077006500")

def test_hypothetical_run_requires_location_and_return_period():
    with pytest.raises(ValidationError):AnalysisRunRequest(mode="hypothetical",hazard_type="flood",return_period_years=100)
    with pytest.raises(ValidationError):AnalysisRunRequest(mode="hypothetical",hazard_type="flood",location=LOCATION)

def test_point_intersection_is_not_a_bbox_touch_test():
    triangle={"type":"Polygon","coordinates":[[[0,0],[4,0],[0,4],[0,0]]]}
    assert point_in_geometry((1,1),triangle); assert not point_in_geometry((3.5,3.5),triangle)

@pytest.mark.asyncio
async def test_zone_membership_returns_screening_and_never_loss(monkeypatch):
    async def fake(location,return_period):
        assert location.tract_geoid=="42077006500" and return_period==100
        return {"zones":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[]},"properties":{"FLD_ZONE":"AE"}}],"sources":[SourceRecord(dataset="NFHL",provider="FEMA",url="https://hazards.fema.gov",version="effective",retrieved_at=datetime.now(timezone.utc),status="loaded")],"totals":AnalysisTotals(structures=12,structure_value_usd=1_000_000,valid_assets=0,excluded_assets=12),"limitations":["No building-level depth."]}
    monkeypatch.setattr(analysis,"run_flood_zone_screening",fake)
    result=await analysis.create_analysis(AnalysisRunRequest(mode="hypothetical",hazard_type="flood",location=LOCATION,return_period_years=100,threshold="100-year / 1% AEP"),Settings())
    assert result.result_type=="exposure_screening" and result.loss is None and result.totals.structures==12
    assert result.manifest.excluded_records["no_compatible_intensity"]==12 and result.manifest.simulation_seed==12345

@pytest.mark.asyncio
async def test_failed_exposure_preserves_hazard(monkeypatch):
    async def fake(location,return_period):return {"zones":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[]},"properties":{}}],"sources":[SourceRecord(dataset="NSI",provider="USACE",url="https://nsi.sec.usace.army.mil",version="2026",retrieved_at=datetime.now(timezone.utc),status="unavailable")],"totals":AnalysisTotals(),"limitations":["NSI unavailable."]}
    monkeypatch.setattr(analysis,"run_flood_zone_screening",fake)
    result=await analysis.create_analysis(AnalysisRunRequest(mode="hypothetical",hazard_type="flood",location=LOCATION,return_period_years=500),Settings())
    assert result.hazard_layers and result.component_status["hazard"]=="loaded" and result.component_status["exposure"]=="unavailable" and result.loss is None
