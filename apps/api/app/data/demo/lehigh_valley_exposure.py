"""Clearly-labelled demonstration exposure for the Bethlehem flood MVP.

Every asset here is synthetic demonstration data (rule 2, rule 13.2): building
footprints do not come with reliable occupancy, construction, replacement value
or first-floor elevation, so those attributes are marked ``MODEL_INFERRED`` or
``DEFAULT_ASSUMPTION`` and must never be shown as observed.

The per-asset ``flood_depth_ft`` values represent a *modelled* 100-year event
depth-at-structure for this demonstration - not a FEMA flood-zone designation
(rule 8) and not a surveyed measurement.
"""

from __future__ import annotations

from app.schemas.catmodel import AttributeOrigin, ExposureAsset

# Origin flags shared by the demo assets. Location and footprint area are the
# only things a building-footprint source would actually give you; everything
# financial or structural is inferred or assumed for this demonstration.
_ORIGINS = {
    "center": AttributeOrigin.PUBLIC_RECORD,
    "floor_area_sqft": AttributeOrigin.PUBLIC_RECORD,
    "occupancy": AttributeOrigin.MODEL_INFERRED,
    "construction": AttributeOrigin.MODEL_INFERRED,
    "number_of_storeys": AttributeOrigin.MODEL_INFERRED,
    "year_built": AttributeOrigin.MODEL_INFERRED,
    "first_floor_elevation_ft": AttributeOrigin.MISSING,
    "replacement_value_usd": AttributeOrigin.DEFAULT_ASSUMPTION,
    "contents_value_usd": AttributeOrigin.DEFAULT_ASSUMPTION,
    "business_interruption_daily_usd": AttributeOrigin.DEFAULT_ASSUMPTION,
}


def _asset(
    asset_id: str,
    name: str,
    center: tuple[float, float],
    occupancy: str,
    construction: str,
    storeys: int,
    year_built: int,
    area: float,
    replacement: float,
    contents: float,
    bi_daily: float,
    ffe: float | None,
    criticality: str = "standard",
) -> ExposureAsset:
    origins = dict(_ORIGINS)
    if ffe is not None:
        origins["first_floor_elevation_ft"] = AttributeOrigin.DEFAULT_ASSUMPTION
    return ExposureAsset(
        asset_id=asset_id,
        name=name,
        center=center,
        occupancy=occupancy,
        construction=construction,
        number_of_storeys=storeys,
        year_built=year_built,
        first_floor_elevation_ft=ffe,
        floor_area_sqft=area,
        replacement_value_usd=replacement,
        contents_value_usd=contents,
        business_interruption_daily_usd=bi_daily,
        criticality=criticality,
        attribute_origins=origins,
    )


# Modelled 100-year depth-at-structure (ft above first-floor grade) for the
# demonstration scenario, keyed by asset_id. Negative = below the modelled
# water surface is not reached (dry).
DEMO_FLOOD_DEPTH_100YR_FT: dict[str, float] = {
    "ex-riverfront-comm-1": 4.2,
    "ex-riverfront-comm-2": 3.1,
    "ex-southside-res-1": 1.8,
    "ex-southside-res-2": 2.6,
    "ex-monocacy-res-1": 3.4,
    "ex-industrial-1": 2.2,
    "ex-hospital-stlukes": 0.0,
    "ex-fire-station-1": 0.4,
    "ex-hillside-res-1": -1.0,
    "ex-hillside-res-2": -1.0,
}


def build_demo_exposure() -> list[ExposureAsset]:
    return [
        _asset("ex-riverfront-comm-1", "Riverfront commercial block A", (-75.3748, 40.6223),
               "commercial", "masonry", 2, 1968, 18000, 4_200_000, 1_600_000, 22_000, ffe=1.0),
        _asset("ex-riverfront-comm-2", "Riverfront commercial block B", (-75.3739, 40.6218),
               "commercial", "masonry", 1, 1974, 9500, 2_300_000, 900_000, 14_000, ffe=1.0),
        _asset("ex-southside-res-1", "South Bethlehem rowhomes 1", (-75.3702, 40.6162),
               "residential", "wood_frame", 2, 1935, 2400, 320_000, 96_000, 0, ffe=1.5),
        _asset("ex-southside-res-2", "South Bethlehem rowhomes 2", (-75.3688, 40.6169),
               "residential", "wood_frame", 2, 1929, 2200, 295_000, 88_000, 0, ffe=1.5),
        _asset("ex-monocacy-res-1", "Monocacy Creek residential", (-75.3792, 40.6271),
               "residential", "wood_frame", 1, 1952, 1600, 240_000, 72_000, 0, ffe=1.0),
        _asset("ex-industrial-1", "South Side light industrial", (-75.3665, 40.6151),
               "industrial", "steel", 1, 1988, 42000, 6_800_000, 4_100_000, 55_000, ffe=1.5),
        _asset("ex-hospital-stlukes", "St. Luke's University Hospital (Fountain Hill)", (-75.3711, 40.6079),
               "hospital", "reinforced_concrete", 6, 1995, 210000, 78_000_000, 34_000_000, 640_000, ffe=3.0,
               criticality="critical"),
        _asset("ex-fire-station-1", "Bethlehem Fire Station 1", (-75.3715, 40.6247),
               "commercial", "masonry", 1, 1961, 8000, 2_100_000, 500_000, 9_000, ffe=1.0,
               criticality="important"),
        _asset("ex-hillside-res-1", "North Bethlehem hillside home 1", (-75.3700, 40.6350),
               "residential", "wood_frame", 2, 2001, 2600, 380_000, 114_000, 0, ffe=2.0),
        _asset("ex-hillside-res-2", "North Bethlehem hillside home 2", (-75.3712, 40.6362),
               "residential", "wood_frame", 2, 2004, 2800, 405_000, 121_000, 0, ffe=2.0),
    ]
