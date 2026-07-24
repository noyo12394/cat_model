from __future__ import annotations
import uuid
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import settings_dep
from app.core.config import Settings
from app.schemas.analysis import AnalysisHazard, AnalysisManifest, AnalysisMode, AnalysisRunRequest, AnalysisRunResult, AnalysisTotals, HazardEventSearchResponse, SourceRecord
from app.services.cat.hazard_providers import provider_for
from app.services.cat.screening import run_flood_zone_screening, run_polygon_exposure_screening

router=APIRouter(prefix="/cat",tags=["cat-analysis"]); CODE_VERSION="riskchain-analysis-0.2.2"

@router.get("/hazard-events",response_model=HazardEventSearchResponse)
async def hazard_events(mode:AnalysisMode,hazard_type:AnalysisHazard,start_date:date|None=None,end_date:date|None=None,settings:Settings=Depends(settings_dep))->HazardEventSearchResponse:
    provider=provider_for(hazard_type,settings)
    if provider is None:
        messages={AnalysisHazard.FLOOD:"Live flood alerts are not runnable without an authoritative inundation footprint.",AnalysisHazard.WILDFIRE:"Wildfire analysis requires an authoritative incident perimeter; no perimeter provider is connected."}
        return HazardEventSearchResponse(events=[],provider="Not configured",retrieved_at=datetime.now(timezone.utc),data_status="unavailable",message=messages.get(hazard_type,"No provider configured."))
    if mode==AnalysisMode.LIVE:return await provider.get_active_events()
    end=end_date or date.today(); start=start_date or end-timedelta(days=30)
    if start>end:raise HTTPException(status_code=422,detail="start_date must be on or before end_date")
    return await provider.search_historical_events(start,end)

@router.get("/hazard-events/{hazard_type}/{event_id}")
async def hazard_event_detail(hazard_type:AnalysisHazard,event_id:str,settings:Settings=Depends(settings_dep))->dict:
    provider=provider_for(hazard_type,settings)
    if provider is None:raise HTTPException(status_code=404,detail="No authoritative provider configured")
    detail=await provider.get_event_details(event_id)
    if not detail:raise HTTPException(status_code=404,detail="Event details unavailable")
    return detail

@router.post("/analyses",response_model=AnalysisRunResult)
async def create_analysis(body:AnalysisRunRequest,settings:Settings=Depends(settings_dep))->AnalysisRunResult:
    now=datetime.now(timezone.utc); run_id=f"run-{uuid.uuid4().hex}"; sources=[]; totals=AnalysisTotals(); layers=[]; limitations=[]
    status={"hazard":"unavailable","exposure":"not loaded","census":"not requested","vulnerability":"not applicable","loss":"not possible"}; title=f"{body.hazard_type.value.title()} exposure screening"
    if body.mode==AnalysisMode.HYPOTHETICAL and body.hazard_type==AnalysisHazard.FLOOD and body.location:
        screening=await run_flood_zone_screening(body.location,body.return_period_years or 100); sources=screening["sources"]; totals=screening["totals"]; limitations=screening["limitations"]; zones=screening["zones"]
        layers=[{"id":"fema-flood-hazard-zones","name":"FEMA effective flood hazard zones","geojson":{"type":"FeatureCollection","features":zones},"classification":"probabilistic hazard","observed_forecast_modelled":"modelled"}] if zones else []
        status["hazard"]="loaded" if zones else "unavailable"; status["exposure"]="loaded" if totals.structures is not None else "unavailable"; status["vulnerability"]="not applied — building-level flood depth unavailable"
        title=f"{body.return_period_years}-year flood — {100/(body.return_period_years or 100):g}% annual exceedance probability"
    else:
        provider=provider_for(body.hazard_type,settings)
        if provider and body.event_id:
            details=await provider.get_event_details(body.event_id,body.advisory_id); footprints=await provider.get_hazard_footprint(body.event_id,body.threshold or "MMI IV+")
            layers=[{"id":"official-hazard-footprint","name":"Official hazard footprint","geojson":{"type":"FeatureCollection","features":footprints},"classification":"observed/modelled","observed_forecast_modelled":"modelled"}] if footprints else []
            status["hazard"]="loaded" if footprints else "event loaded; usable intensity footprint unavailable"
            if footprints:
                screening=await run_polygon_exposure_screening(footprints); sources=screening["sources"]; totals=screening["totals"]; limitations=screening["limitations"]
                status["exposure"]="loaded" if totals.structures is not None else "unavailable"
                source=provider.get_source_metadata(); sources.insert(0, SourceRecord(dataset="Official hazard footprint",provider=source["provider"],url=source["url"],version=body.advisory_id or "current advisory",retrieved_at=now,status="loaded",note="Published official geometry used for exposure screening."))
            else:
                limitations.append("The epicenter or track is not treated as an impact area.")
            title=details.get("properties",{}).get("title") or body.event_id
        else:limitations.append("No compatible authoritative provider or footprint is available.")
    missing=[]
    if not layers:missing.append("usable hazard-intensity footprint")
    if totals.structures is None:missing.append("exposure records intersecting the footprint")
    missing.append("compatible asset-level hazard intensity for damage calculation")
    confidence={"overall":"low","components":{"hazard":"moderate" if layers else "low","exposure":"moderate" if totals.structures is not None else "low","vulnerability":"not applicable"},"explanation":"This is a screening result. Compatible asset-level intensity is unavailable, so damage and loss are not estimated.","ways_to_improve":["Provide a defensible depth/intensity surface","Validate structure attributes locally","Select a compatible versioned vulnerability function"]}
    manifest=AnalysisManifest(run_id=run_id,created_at=now,code_version=CODE_VERSION,inputs=body.model_dump(mode="json"),provider_event_ids={body.provider or body.hazard_type.value:body.event_id} if body.event_id else {},advisory_versions=[body.advisory_id] if body.advisory_id else [],geographic_boundaries={"bbox":body.location.bbox,"center":body.location.center} if body.location else {},sources=sources,vulnerability_function_ids=[],assumptions=["FEMA zone membership is exposure screening only"] if body.hazard_type==AnalysisHazard.FLOOD else [],missing_fields=missing,excluded_records={"no_compatible_intensity":totals.excluded_assets},simulation_seed=body.seed,simulation_count=body.simulation_count,calculation_summary="Exposure attributes were aggregated only where source data were present. No loss calculation was permitted.")
    return AnalysisRunResult(run_id=run_id,result_type="exposure_screening",mode=body.mode,hazard_type=body.hazard_type,title=title,provider_event_id=body.event_id,analysis_time=now,geography=body.location,hazard_threshold=body.threshold,hazard_layers=layers,totals=totals,confidence=confidence,component_status=status,limitations=limitations,loss=None,manifest=manifest)
