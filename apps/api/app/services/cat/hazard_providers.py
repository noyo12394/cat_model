"""Common authoritative hazard-provider interface and first connectors."""
from __future__ import annotations
import asyncio
from datetime import date, datetime, time, timedelta, timezone
from typing import Protocol
from urllib.parse import urlparse
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


class NWSFloodAlertProvider:
    """Current NWS flood-alert polygons for a *screening* workflow.

    An NWS warning or watch polygon is an official alert area, not a surveyed
    flood extent or a depth/intensity surface.  It can nevertheless support a
    bounded ``which NSI structures intersect this alert area?`` screen.  The
    provider deliberately does not offer a historical catalogue: NWS's active
    alerts endpoint is not an archive and substituting a different source here
    would make the model workflow look more capable than it is.
    """

    _ACTIVE_ALERTS_URL = "https://api.weather.gov/alerts/active"
    _EVENTS = ("Flood Warning", "Flash Flood Warning", "Flood Watch")
    _ALLOWED_HOST = "api.weather.gov"

    @staticmethod
    def _has_polygon(feature: dict) -> bool:
        geometry = feature.get("geometry") or {}
        return geometry.get("type") in {"Polygon", "MultiPolygon"} and bool(geometry.get("coordinates"))

    @classmethod
    def _safe_alert_url(cls, event_id: str) -> str | None:
        """Accept only an alert URL issued by the official NWS API.

        Event IDs arrive from the selected catalogue, but this guard keeps a
        crafted API request from turning the event-detail route into an SSRF
        primitive.
        """
        parsed = urlparse(event_id)
        if parsed.scheme != "https" or parsed.netloc != cls._ALLOWED_HOST:
            return None
        if not parsed.path.startswith("/alerts/"):
            return None
        return event_id

    @classmethod
    def _summary(cls, feature: dict) -> HazardEventSummary | None:
        properties = feature.get("properties") or {}
        event_id = properties.get("@id") or feature.get("id")
        if not isinstance(event_id, str) or not cls._safe_alert_url(event_id):
            return None
        event = str(properties.get("event") or "Flood alert")
        area = str(properties.get("areaDesc") or "affected area")
        headline = str(properties.get("headline") or f"{event} — {area}")
        is_watch = event.lower() == "flood watch"
        limitations = [
            "NWS alert geometry identifies an alert area, not a flood-inundation extent or water-depth surface.",
            "The resulting output is exposure screening only; no damage or dollar loss is calculated.",
        ]
        if not cls._has_polygon(feature):
            limitations.insert(0, "This alert has no published polygon and is therefore not runnable as a spatial screen.")
        return HazardEventSummary(
            provider="NWS",
            provider_event_id=event_id,
            hazard_type="flood",
            name=headline,
            status=str(properties.get("status") or properties.get("severity") or "active"),
            start_time=properties.get("effective") or properties.get("onset"),
            update_time=properties.get("sent") or properties.get("updated"),
            center=None,
            source_url=event_id,
            source_version=str(properties.get("sent") or properties.get("id") or "active alert"),
            classification="forecast" if is_watch else "observed",
            advisory_id=str(properties.get("id") or event_id),
            footprint_available=cls._has_polygon(feature),
            limitations=limitations,
        )

    async def _active_features(self) -> list[dict]:
        responses = await asyncio.gather(
            *(safe_get_json(self._ACTIVE_ALERTS_URL, {"event": event}) for event in self._EVENTS),
        )
        unique: dict[str, dict] = {}
        for payload in responses:
            if not isinstance(payload, dict):
                continue
            for feature in payload.get("features", []):
                if not isinstance(feature, dict):
                    continue
                properties = feature.get("properties") or {}
                identifier = properties.get("@id") or feature.get("id")
                if isinstance(identifier, str):
                    unique[identifier] = feature
        return list(unique.values())

    async def get_active_events(self) -> HazardEventSearchResponse:
        retrieved_at = datetime.now(timezone.utc)
        features = await self._active_features()
        if not features:
            return HazardEventSearchResponse(
                events=[],
                provider="National Weather Service",
                retrieved_at=retrieved_at,
                data_status="unavailable",
                message="No active NWS flood warning, flash-flood warning, or flood watch could be retrieved. No substitute alert is shown.",
            )
        events = [summary for feature in features if (summary := self._summary(feature))]
        events.sort(key=lambda event: event.update_time or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return HazardEventSearchResponse(
            events=events,
            provider="National Weather Service",
            retrieved_at=retrieved_at,
            data_status="live",
            message=None if events else "NWS returned no usable flood-alert records.",
        )

    async def search_historical_events(self, start: date, end: date) -> HazardEventSearchResponse:
        return HazardEventSearchResponse(
            events=[],
            provider="National Weather Service",
            retrieved_at=datetime.now(timezone.utc),
            data_status="unavailable",
            message="NWS active alerts are not a historical flood archive. NOAA Storm Events can be explored as an external archive, but it is not connected as a runnable footprint source.",
        )

    async def _feature_for_event(self, event_id: str) -> dict | None:
        safe_url = self._safe_alert_url(event_id)
        if not safe_url:
            return None
        payload = await safe_get_json(safe_url)
        if isinstance(payload, dict) and payload.get("type") == "Feature":
            return payload
        if isinstance(payload, dict):
            features = payload.get("features") or []
            return features[0] if features and isinstance(features[0], dict) else None
        return None

    async def get_event_details(self, event_id: str, advisory_id: str | None = None) -> dict:
        feature = await self._feature_for_event(event_id)
        if not feature:
            return {}
        properties = feature.get("properties") or {}
        return {"properties": {"title": properties.get("headline") or properties.get("event") or "NWS flood alert"}, "event": feature}

    async def get_hazard_footprint(self, event_id: str, threshold: str) -> list[dict]:
        feature = await self._feature_for_event(event_id)
        return [feature] if feature and self._has_polygon(feature) else []

    def get_source_metadata(self) -> dict:
        return {"provider": "National Weather Service", "url": "https://www.weather.gov/documentation/services-web-api"}

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
        # FDSN resolves both global ``us`` ids and regional-network ids such as
        # ``ci``/``ak``.  The feed detail URL returns 404 for older regional
        # events even when the catalog correctly advertises a ShakeMap.
        payload=await safe_get_json(f"{self.base_url}/query",{"eventid":event_id,"format":"geojson"}); return payload if isinstance(payload,dict) else {}
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
    if hazard==AnalysisHazard.FLOOD:return NWSFloodAlertProvider()
    if hazard==AnalysisHazard.WILDFIRE:
        from app.services.cat.wildfire_provider import NIFCWildfireProvider
        return NIFCWildfireProvider()
    return None
