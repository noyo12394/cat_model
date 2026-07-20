"""Common authoritative hazard-provider interface and first connectors."""
from __future__ import annotations
from datetime import date, datetime, time, timedelta, timezone
from typing import Protocol
from app.adapters.base import safe_get_json
from app.adapters.nhc import fetch_nhc_forecast_tracks, fetch_nhc_forecast_wind_radii
from app.core.config import Settings
from app.schemas.analysis import AnalysisHazard, HazardEventSearchResponse, HazardEventSummary

class HazardProvider(Protocol):
    async def get_active_events(self)->HazardEventSearchResponse: ...
    async def search_historical_events(self,start:date,end:date)->HazardEventSearchResponse: ...
    async def get_event_details(self,event_id:str,advisory_id:str|None=None)->dict: ...
    async def get_hazard_footprint(self,event_id:str,threshold:str)->list[dict]: ...
    def get_source_metadata(self)->dict: ...

class NHCProvider:
    async def get_active_events(self)->HazardEventSearchResponse:
        response=await fetch_nhc_forecast_tracks()
        events=[HazardEventSummary(provider="NHC",provider_event_id=t.event_id,hazard_type="hurricane",name=f"{t.storm_type} {t.name}",status="active",start_time=t.valid_from,update_time=t.observed_at,center=t.points[0].center if t.points else None,source_url=t.advisory_url,source_version=t.observed_at.isoformat() if t.observed_at else "current feed",classification="forecast",advisory_id=t.observed_at.isoformat() if t.observed_at else None,footprint_available=bool(t.wind_field_url),limitations=[] if t.wind_field_url else ["The forecast track is not an impact footprint. This advisory has no published NHC forecast-wind GIS product."]) for t in response.items]
        message=None if events else ("No active NHC tropical cyclone is currently available." if response.status.value=="live" else "The official NHC feed is unavailable; no substitute event is shown.")
        return HazardEventSearchResponse(events=events,provider="National Hurricane Center",retrieved_at=response.retrieved_at,data_status="live" if response.status.value=="live" else "unavailable",message=message)
    async def search_historical_events(self,start:date,end:date)->HazardEventSearchResponse:
        return HazardEventSearchResponse(events=[],provider="National Hurricane Center",retrieved_at=datetime.now(timezone.utc),data_status="unavailable",message="Historical NHC best-track search is not connected in this release.")
    async def get_event_details(self,event_id:str,advisory_id:str|None=None)->dict:
        response=await self.get_active_events(); event=next((x for x in response.events if x.provider_event_id==event_id),None)
        return {"properties":{"title":event.name},"event":event.model_dump(mode="json")} if event else {}
    async def get_hazard_footprint(self,event_id:str,threshold:str)->list[dict]:
        response=await fetch_nhc_forecast_tracks(); track=next((item for item in response.items if item.event_id==event_id),None)
        if not track or "34-knot" not in threshold.lower(): return []
        return await fetch_nhc_forecast_wind_radii(track,34)
    def get_source_metadata(self)->dict: return {"provider":"NHC","url":"https://www.nhc.noaa.gov/gis/"}

class USGSEarthquakeProvider:
    def __init__(self,settings:Settings): self.base_url=settings.usgs_quake_base_url.replace("/earthquakes/feed/v1.0","/fdsnws/event/1")
    async def _query(self,start:datetime,end:datetime,minimum_magnitude:float)->HazardEventSearchResponse:
        payload=await safe_get_json(f"{self.base_url}/query",{"format":"geojson","starttime":start.isoformat(),"endtime":end.isoformat(),"minmagnitude":minimum_magnitude,"orderby":"time","limit":200})
        if not isinstance(payload,dict): return HazardEventSearchResponse(events=[],provider="U.S. Geological Survey",retrieved_at=datetime.now(timezone.utc),data_status="unavailable",message="USGS catalog unavailable; no substitute event is shown.")
        events=[]
        for feature in payload.get("features",[]):
            try:
                p,c=feature["properties"],feature["geometry"]["coordinates"]
                observed=datetime.fromtimestamp(p["time"]/1000,timezone.utc); updated=datetime.fromtimestamp(p["updated"]/1000,timezone.utc); has="shakemap" in (p.get("types") or "")
                events.append(HazardEventSummary(provider="USGS",provider_event_id=feature["id"],hazard_type="earthquake",name=p.get("title") or "Earthquake",status=p.get("status","reviewed"),start_time=observed,update_time=updated,center=(float(c[0]),float(c[1])),source_url=p.get("detail") or p.get("url"),source_version=str(p.get("code") or updated.isoformat()),classification="observed",footprint_available=has,limitations=[] if has else ["No ShakeMap is advertised; the epicenter is not an impact polygon."]))
            except (KeyError,TypeError,ValueError): continue
        return HazardEventSearchResponse(events=events,provider="U.S. Geological Survey",retrieved_at=datetime.now(timezone.utc),data_status="live",message=None if events else "No USGS earthquakes matched these filters.")
    async def get_active_events(self)->HazardEventSearchResponse:
        end=datetime.now(timezone.utc); return await self._query(end-timedelta(days=1),end,2.5)
    async def search_historical_events(self,start:date,end:date)->HazardEventSearchResponse:
        return await self._query(datetime.combine(start,time.min,timezone.utc),datetime.combine(end,time.max,timezone.utc),2.5)
    async def get_event_details(self,event_id:str,advisory_id:str|None=None)->dict:
        payload=await safe_get_json(f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/{event_id}.geojson"); return payload if isinstance(payload,dict) else {}
    async def get_hazard_footprint(self,event_id:str,threshold:str)->list[dict]:
        detail=await self.get_event_details(event_id); products=detail.get("properties",{}).get("products",{}).get("shakemap",[])
        if not products:return []
        preferred=max(products,key=lambda x:x.get("preferredWeight",0)); contour=next((v for k,v in preferred.get("contents",{}).items() if k.endswith("cont_mi.json")),None)
        if not contour or not contour.get("url"):return []
        payload=await safe_get_json(contour["url"])
        if not isinstance(payload,dict):return []
        try: minimum=float(threshold.lower().replace("mmi","").replace("+","").strip())
        except ValueError: minimum=4
        return [f for f in payload.get("features",[]) if float(f.get("properties",{}).get("value",f.get("properties",{}).get("mmi",0)))>=minimum]
    def get_source_metadata(self)->dict:return {"provider":"USGS","url":"https://earthquake.usgs.gov/fdsnws/event/1/"}

def provider_for(hazard:AnalysisHazard,settings:Settings)->HazardProvider|None:
    if hazard==AnalysisHazard.HURRICANE:return NHCProvider()
    if hazard==AnalysisHazard.EARTHQUAKE:return USGSEarthquakeProvider(settings)
    if hazard==AnalysisHazard.WILDFIRE:
        from app.services.cat.wildfire_provider import NIFCWildfireProvider
        return NIFCWildfireProvider()
    return None
