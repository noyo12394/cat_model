"""Authoritative U.S. Census coordinate-to-geography lookup."""
from __future__ import annotations
from dataclasses import dataclass
import httpx

@dataclass(frozen=True)
class CensusGeography:
    state: str | None = None
    state_fips: str | None = None
    county: str | None = None
    county_fips: str | None = None
    tract: str | None = None
    tract_geoid: str | None = None
    vintage: str = "Current_Current"

def _first(geographies: dict, *names: str) -> dict:
    for name in names:
        rows = geographies.get(name)
        if isinstance(rows, list) and rows:
            return rows[0]
    return {}

async def lookup_geography(lon: float, lat: float) -> CensusGeography | None:
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return None
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get("https://geocoding.geo.census.gov/geocoder/geographies/coordinates", params={"x": lon, "y": lat, "benchmark": "Public_AR_Current", "vintage": "Current_Current", "format": "json"}, headers={"User-Agent": "RiskChain-CAT/0.2"})
        response.raise_for_status()
        geographies = response.json()["result"]["geographies"]
        state, county, tract = _first(geographies, "States"), _first(geographies, "Counties"), _first(geographies, "Census Tracts")
        if not state and not county and not tract:
            return None
        state_code = str(state.get("STATE") or state.get("GEOID") or "") or None
        county_code = str(county.get("COUNTY") or "") or None
        return CensusGeography(state=state.get("NAME"), state_fips=state_code, county=county.get("NAME"), county_fips=f"{state_code}{county_code}" if state_code and county_code else county.get("GEOID"), tract=tract.get("NAME"), tract_geoid=tract.get("GEOID"))
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return None
