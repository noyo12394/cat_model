from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.api.v1 import analysis
from app.core.config import Settings
from app.schemas.analysis import AnalysisLocation, AnalysisRunRequest, AnalysisTotals, SourceRecord
from app.services.cat.screening import _prepared_nsi_features, _screening_budget, point_in_geometry

LOCATION=AnalysisLocation(place_id="bethlehem-pa",name="Bethlehem, Pennsylvania",center=(-75.3705,40.6259),bbox=(-75.40,40.60,-75.34,40.65),state="Pennsylvania",state_fips="42",county="Lehigh County",county_fips="42077",tract="Census Tract 65",tract_geoid="42077006500")

def test_hypothetical_run_requires_location_and_return_period():
    with pytest.raises(ValidationError):AnalysisRunRequest(mode="hypothetical",hazard_type="flood",return_period_years=100)
    with pytest.raises(ValidationError):AnalysisRunRequest(mode="hypothetical",hazard_type="flood",location=LOCATION)

def test_point_intersection_is_not_a_bbox_touch_test():
    triangle={"type":"Polygon","coordinates":[[[0,0],[4,0],[0,4],[0,0]]]}
    assert point_in_geometry((1,1),triangle); assert not point_in_geometry((3.5,3.5),triangle)

def test_oversized_official_footprint_is_kept_but_not_sent_to_nsi():
    # This is a request-safety guard, not an intensity or area calculation.
    # A broad forecast geometry must return a prompt hazard-only screen rather
    # than timing out or replacing the missing exposure response with a value.
    features=[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[-80,20],[-70,20],[-70,30],[-80,30],[-80,20]]]},"properties":{}}]
    within_budget, reason=_screening_budget(features)
    assert not within_budget and reason and "broad" in reason

def test_high_vertex_perimeter_uses_a_bounded_simplified_provider_geometry():
    # Simplification is a documented request adaptation, never a new map layer
    # or an invented intensity field. The original boundary is retained by the
    # analysis result while the smaller copy is sent only to USACE.
    ring=[[index / 100_000, 0.0] for index in range(5_200)] + [[0.052, 0.05], [0.0, 0.0]]
    features=[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[ring]},"properties":{}}]
    prepared, note=_prepared_nsi_features(features)
    assert prepared is not None and note and "simplified" in note
    assert len(prepared[0]["geometry"]["coordinates"][0]) <= 5_000

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


@pytest.mark.asyncio
async def test_official_event_polygon_runs_exposure_screening_without_loss(monkeypatch):
    class Provider:
        async def get_event_details(self,event_id,advisory_id=None): return {"properties":{"title":"Official wind-field advisory"}}
        async def get_hazard_footprint(self,event_id,threshold):
            assert threshold=="Official forecast 34-knot wind field"
            return [{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[-76,40],[-75,40],[-75,41],[-76,40]]]},"properties":{"wind_radius_knots":34}}]
        def get_source_metadata(self): return {"provider":"National Hurricane Center","url":"https://www.nhc.noaa.gov/gis/"}
    async def fake_screening(footprints):
        assert footprints[0]["properties"]["wind_radius_knots"]==34
        return {"sources":[SourceRecord(dataset="NSI",provider="USACE",url="https://nsi.sec.usace.army.mil",version="2026",retrieved_at=datetime.now(timezone.utc),status="loaded")],"totals":AnalysisTotals(structures=18,population=42,structure_value_usd=2_000_000,contents_value_usd=750_000,excluded_assets=18),"limitations":["No asset-level wind intensity."]}
    monkeypatch.setattr(analysis,"provider_for",lambda hazard,settings:Provider())
    monkeypatch.setattr(analysis,"run_polygon_exposure_screening",fake_screening)
    result=await analysis.create_analysis(AnalysisRunRequest(mode="live",hazard_type="hurricane",event_id="NHC-AL022026",provider="NHC",threshold="Official forecast 34-knot wind field"),Settings())
    assert result.result_type=="exposure_screening" and result.loss is None
    assert result.component_status["hazard"]=="loaded" and result.component_status["exposure"]=="loaded"
    assert result.totals.structures==18 and result.manifest.excluded_records["no_compatible_intensity"]==18
