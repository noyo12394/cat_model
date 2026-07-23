"""FEMA NFHL and USACE NSI exposure screening with true point/polygon tests."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import asyncio
import httpx
from app.schemas.analysis import AnalysisLocation, AnalysisTotals, SourceRecord

FEMA_NFHL_URL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
NSI_URL = "https://nsi.sec.usace.army.mil/nsiapi/structures"
# The NSI endpoint accepts polygons, but a national-scale forecast wind field
# can imply an unbounded number of candidate structures.  Keep the interactive
# workflow responsive by declining that *exposure* request before it becomes a
# timeout.  The authoritative hazard geometry is still returned by the caller;
# this only prevents an unsafe aggregation request and never substitutes data.
MAX_NSI_SCREENING_VERTICES = 5_000
MAX_NSI_SCREENING_BBOX_DEGREES_SQUARED = 4.0

def _rings(geometry: dict[str, Any]) -> list[list[list[float]]]:
    if geometry.get("type") == "Polygon": return geometry.get("coordinates", [])
    if geometry.get("type") == "MultiPolygon": return [ring for polygon in geometry.get("coordinates", []) for ring in polygon]
    return []

def _screening_budget(features: list[dict[str, Any]]) -> tuple[bool, str | None]:
    """Return whether an official geometry is safe for one NSI polygon query.

    This is intentionally a request-budget check, not an estimate of a hazard
    area.  It keeps large forecast products from blocking the UI and preserves
    the distinction between a published footprint and an exposure calculation.
    """
    positions = [position for feature in features for ring in _rings(feature.get("geometry") or {}) for position in ring if len(position) >= 2]
    if not positions:
        return False, "The official product did not contain polygon coordinates usable by the exposure service."
    if len(positions) > MAX_NSI_SCREENING_VERTICES:
        return False, f"The official footprint has {len(positions):,} vertices, above the interactive screening request limit."
    try:
        longitudes = [float(position[0]) for position in positions]
        latitudes = [float(position[1]) for position in positions]
    except (TypeError, ValueError):
        return False, "The official product contained coordinates that could not be validated for the exposure service."
    bbox_area = (max(longitudes) - min(longitudes)) * (max(latitudes) - min(latitudes))
    if bbox_area > MAX_NSI_SCREENING_BBOX_DEGREES_SQUARED:
        return False, "The official footprint covers too broad an area for one interactive NSI screening request."
    return True, None

def _inside_ring(point: tuple[float, float], ring: list[list[float]]) -> bool:
    x, y, inside, j = point[0], point[1], False, len(ring) - 1
    for i, current in enumerate(ring):
        xi, yi, xj, yj = current[0], current[1], ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi: inside = not inside
        j = i
    return inside

def point_in_geometry(point: tuple[float, float], geometry: dict[str, Any]) -> bool:
    rings = _rings(geometry)
    return bool(rings and _inside_ring(point, rings[0]) and not any(_inside_ring(point, hole) for hole in rings[1:]))

async def _query_nsi_polygons(client: httpx.AsyncClient, features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collection={"type":"FeatureCollection","features":features}
    response=await client.post(f"{NSI_URL}?fmt=fc",json=collection)
    if response.status_code==413 and len(features)>1:
        middle=len(features)//2
        left,right=await asyncio.gather(_query_nsi_polygons(client,features[:middle]),_query_nsi_polygons(client,features[middle:]))
        return left+right
    if response.status_code==413:
        return []
    response.raise_for_status()
    return response.json().get("features",[])

def _bbox(location: AnalysisLocation) -> tuple[float, float, float, float]:
    if location.bbox:
        west, south, east, north = location.bbox
        if east - west <= .25 and north - south <= .25: return location.bbox
    lon, lat = location.center
    return lon - .025, lat - .02, lon + .025, lat + .02

async def run_flood_zone_screening(location: AnalysisLocation, return_period: int) -> dict[str, Any]:
    retrieved_at, bounds = datetime.now(timezone.utc), _bbox(location)
    west, south, east, north = bounds
    sources: list[SourceRecord] = []
    limitations = ["FEMA flood-hazard zones are probabilistic/regulatory areas, not a live inundation footprint.", "Zone membership does not provide a defensible structure-level water depth; no damage or dollar loss is calculated.", "NSI is a modelled national inventory intended for screening, not verified structure-level appraisal."]
    zones: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(FEMA_NFHL_URL, params={"f":"geojson","where":"1=1","geometry":f"{west},{south},{east},{north}","geometryType":"esriGeometryEnvelope","inSR":4326,"spatialRel":"esriSpatialRelIntersects","outSR":4326,"outFields":"FLD_ZONE,ZONE_SUBTY,SFHA_TF,STATIC_BFE,DEPTH,LEN_UNIT,SOURCE_CIT","returnGeometry":"true"})
        response.raise_for_status(); zones = response.json().get("features", [])
        if return_period in {50,100}: zones = [f for f in zones if str(f.get("properties",{}).get("SFHA_TF","")).upper()=="T"]
        elif return_period == 500: zones = [f for f in zones if "0.2" in str(f.get("properties",{}).get("ZONE_SUBTY",""))]
        sources.append(SourceRecord(dataset="National Flood Hazard Layer — Flood Hazard Zones",provider="FEMA",url=FEMA_NFHL_URL,version="effective NFHL",retrieved_at=retrieved_at,status="loaded",note=f"{len(zones)} intersecting polygons matched."))
    except (httpx.HTTPError, ValueError, TypeError):
        sources.append(SourceRecord(dataset="National Flood Hazard Layer — Flood Hazard Zones",provider="FEMA",url=FEMA_NFHL_URL,version="effective NFHL",retrieved_at=retrieved_at,status="unavailable",note="Request failed; no substitute was used."))
    structures: list[dict[str,Any]] = []
    if zones:
        try:
            # NSI's documented polygon POST performs the spatial clip on the
            # provider side. This is a true geometry query, not a bbox count,
            # and avoids an O(points × polygons) interactive request.
            hazard_features=[{"type":"Feature","geometry":zone.get("geometry"),"properties":{}} for zone in zones if zone.get("geometry")]
            async with httpx.AsyncClient(timeout=20.0) as client: features=await _query_nsi_polygons(client,hazard_features)
            if len(features)>10000: raise ValueError("NSI response exceeded safe limit")
            unique:dict[str,dict[str,Any]]={}
            for feature in features:
                props=feature.get("properties",{}); key=str(props.get("fd_id") or props.get("bid") or feature.get("id") or feature.get("geometry"))
                unique[key]=feature
            structures=list(unique.values())
            sources.append(SourceRecord(dataset="National Structure Inventory 2026 Base",provider="USACE",url=NSI_URL,version="2026 Base",retrieved_at=retrieved_at,status="loaded",note=f"{len(structures)} points intersected FEMA polygons."))
        except (httpx.HTTPError,ValueError,TypeError,KeyError):
            sources.append(SourceRecord(dataset="National Structure Inventory 2026 Base",provider="USACE",url=NSI_URL,version="2026 Base",retrieved_at=retrieved_at,status="unavailable",note="Request failed or exceeded safe limit; hazard was preserved."))
    def vals(*keys: str) -> list[float]:
        output=[]
        for item in structures:
            props=item.get("properties",{})
            value=next((props.get(k) for k in keys if isinstance(props.get(k),(int,float))),None)
            if value is not None: output.append(float(value))
        return output
    sv,cv,pv=vals("val_struct","val_struct_d"),vals("val_cont","val_cont_d"),vals("pop2amu65","pop2pmu65")
    loaded=any(s.dataset.startswith("National Structure") and s.status=="loaded" for s in sources)
    totals=AnalysisTotals(structures=len(structures) if loaded else None,population=round(sum(pv)) if pv else None,structure_value_usd=sum(sv) if sv else None,contents_value_usd=sum(cv) if cv else None,valid_assets=0,excluded_assets=len(structures))
    return {"zones":zones,"sources":sources,"totals":totals,"limitations":limitations}


async def run_polygon_exposure_screening(footprints: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate NSI exposure strictly inside supplied authoritative polygons.

    The caller owns the hazard source and classification.  This function never
    infers intensity or loss from a footprint; it only reports the exposure
    records returned by USACE's documented polygon intersection endpoint.
    """
    retrieved_at = datetime.now(timezone.utc)
    sources: list[SourceRecord] = []
    structures: list[dict[str, Any]] = []
    hazard_features = [
        {"type": "Feature", "geometry": feature.get("geometry"), "properties": {}}
        for feature in footprints
        if feature.get("geometry")
    ]
    if hazard_features:
        within_budget, budget_reason = _screening_budget(hazard_features)
        if not within_budget:
            sources.append(SourceRecord(dataset="National Structure Inventory 2026 Base", provider="USACE", url=NSI_URL, version="2026 Base", retrieved_at=retrieved_at, status="not_applicable", note=f"Exposure aggregation was not requested. {budget_reason} Select a smaller area of interest before running an exposure screen."))
        else:
            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    features = await _query_nsi_polygons(client, hazard_features)
                if len(features) > 10_000:
                    raise ValueError("NSI response exceeded safe limit")
                unique: dict[str, dict[str, Any]] = {}
                for feature in features:
                    props = feature.get("properties", {})
                    key = str(props.get("fd_id") or props.get("bid") or feature.get("id") or feature.get("geometry"))
                    unique[key] = feature
                structures = list(unique.values())
                sources.append(SourceRecord(dataset="National Structure Inventory 2026 Base", provider="USACE", url=NSI_URL, version="2026 Base", retrieved_at=retrieved_at, status="loaded", note=f"{len(structures)} points intersected the supplied official hazard polygons."))
            except (httpx.HTTPError, ValueError, TypeError, KeyError):
                sources.append(SourceRecord(dataset="National Structure Inventory 2026 Base", provider="USACE", url=NSI_URL, version="2026 Base", retrieved_at=retrieved_at, status="unavailable", note="Request failed or exceeded the safe screening limit; no substitute exposure values were used."))

    def vals(*keys: str) -> list[float]:
        output: list[float] = []
        for item in structures:
            props = item.get("properties", {})
            value = next((props.get(key) for key in keys if isinstance(props.get(key), (int, float))), None)
            if value is not None:
                output.append(float(value))
        return output

    structure_values = vals("val_struct", "val_struct_d")
    contents_values = vals("val_cont", "val_cont_d")
    population_values = vals("pop2amu65", "pop2pmu65")
    loaded = any(source.dataset.startswith("National Structure") and source.status == "loaded" for source in sources)
    totals = AnalysisTotals(structures=len(structures) if loaded else None, population=round(sum(population_values)) if population_values else None, structure_value_usd=sum(structure_values) if structure_values else None, contents_value_usd=sum(contents_values) if contents_values else None, valid_assets=0, excluded_assets=len(structures))
    limitations = ["Hazard-polygon membership is exposure screening only. Asset-level wind intensity and compatible vulnerability are not available, so no damage or dollar loss is calculated.", "NSI is a modelled national inventory for screening, not verified structure-level appraisal."]
    if any(source.status == "not_applicable" for source in sources):
        limitations.append("The official footprint was preserved, but its geographic extent exceeded the bounded interactive exposure-screening request. No exposure count was inferred.")
    return {"sources": sources, "totals": totals, "limitations": limitations}
