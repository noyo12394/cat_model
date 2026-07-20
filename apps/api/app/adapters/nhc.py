"""National Hurricane Center official forecast-track adapter.

The NHC GIS feeds are used only for named tropical cyclones in their published
Atlantic and eastern Pacific basins.  This module intentionally does not turn
the product into a global all-hazard prediction service: if NHC has no
forecast track for a selected date, callers receive no event rather than an
invented one.
"""

from __future__ import annotations

import io
import re
import struct
import time
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from app.adapters.base import AdapterResponse, safe_get_bytes
from app.schemas.enums import DataStatus

_CACHE_TTL_SECONDS = 300
_NHC_NAMESPACE = "https://www.nhc.noaa.gov"
_BASINS = {
    "Atlantic": "https://www.nhc.noaa.gov/gis-at.xml",
    "Eastern Pacific": "https://www.nhc.noaa.gov/gis-ep.xml",
}
_NHC_TIMEZONE_OFFSETS = {"EDT": -4, "EST": -5, "CDT": -5, "CST": -6, "PDT": -7, "PST": -8, "AST": -4, "HST": -10}
_cache: tuple[float, AdapterResponse["NHCForecastTrack"]] | None = None


@dataclass(frozen=True)
class NHCForecastPoint:
    valid_at: datetime
    center: tuple[float, float]


@dataclass
class NHCForecastTrack:
    event_id: str
    name: str
    storm_type: str
    basin: str
    observed_at: datetime | None
    headline: str | None
    advisory_url: str
    track_url: str
    shape_url: str | None = None
    wind_field_url: str | None = None
    points: list[NHCForecastPoint] = field(default_factory=list)

    @property
    def valid_from(self) -> datetime | None:
        return min((point.valid_at for point in self.points), default=None)

    @property
    def valid_to(self) -> datetime | None:
        return max((point.valid_at for point in self.points), default=None)


def _as_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            match = re.search(
                r"(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<time>\d{1,2}:\d{2}\s+[AP]M)\s+\w{3}\s+(?P<zone>[A-Z]{3})",
                value,
            )
            if not match or match.group("zone") not in _NHC_TIMEZONE_OFFSETS:
                return None
            try:
                parsed = datetime.strptime(f"{match.group('date')} {match.group('time')}", "%Y-%m-%d %I:%M %p")
            except ValueError:
                return None
            parsed = parsed.replace(tzinfo=timezone(timedelta(hours=_NHC_TIMEZONE_OFFSETS[match.group("zone")])))
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _child_text(parent: ET.Element, tag: str) -> str | None:
    node = parent.find(f"{{{_NHC_NAMESPACE}}}{tag}")
    return node.text.strip() if node is not None and node.text else None


def _parse_feed(payload: bytes, basin: str) -> list[NHCForecastTrack]:
    """Extract active named storms and their published Forecast Track KMZ URL."""
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return []

    items = root.findall("./channel/item")
    product_links: dict[str, dict[str, str]] = {}
    for item in items:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        if not (link.endswith(".kmz") or link.endswith(".zip")) or ("Forecast" not in title and "Wind Field" not in title):
            continue
        match = re.search(r"\((?:[^/]+)/([^\)]+)\)", title)
        if match:
            atcf_id = match.group(1).strip()
            products = product_links.setdefault(atcf_id, {})
            if "Forecast Track [kmz]" in title:
                products["track"] = link.strip()
            elif "Forecast [shp]" in title:
                products["shape"] = link.strip()
            elif "Wind Field [shp]" in title:
                products["wind_field"] = link.strip()

    tracks: list[NHCForecastTrack] = []
    for item in items:
        cyclone = item.find(f"{{{_NHC_NAMESPACE}}}Cyclone")
        if cyclone is None:
            continue
        atcf_id = _child_text(cyclone, "atcf")
        name = _child_text(cyclone, "name")
        products = product_links.get(atcf_id or "", {})
        if not atcf_id or not name or "track" not in products:
            continue
        tracks.append(
            NHCForecastTrack(
                event_id=f"NHC-{atcf_id}",
                name=name,
                storm_type=_child_text(cyclone, "type") or "Tropical cyclone",
                basin=basin,
                observed_at=_as_utc(item.findtext("pubDate")),
                headline=_child_text(cyclone, "headline"),
                advisory_url=(item.findtext("link") or "https://www.nhc.noaa.gov/").strip(),
                track_url=products["track"],
                shape_url=products.get("shape"),
                wind_field_url=products.get("wind_field"),
            )
        )
    return tracks


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_track_points(payload: bytes) -> list[NHCForecastPoint]:
    """Read only timestamped official forecast points from an NHC track KMZ."""
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            kml_name = next(name for name in archive.namelist() if name.lower().endswith(".kml"))
            root = ET.fromstring(archive.read(kml_name))
    except (ET.ParseError, OSError, StopIteration, zipfile.BadZipFile):
        return []

    points: list[NHCForecastPoint] = []
    for placemark in (node for node in root.iter() if _local_name(node.tag) == "Placemark"):
        when = next((node.text for node in placemark.iter() if _local_name(node.tag) == "when" and node.text), None)
        coordinates = next((node.text for node in placemark.iter() if _local_name(node.tag) == "coordinates" and node.text), None)
        valid_at = _as_utc(when)
        if not valid_at or not coordinates:
            continue
        try:
            lon_text, lat_text, *_ = coordinates.strip().split()[0].split(",")
            center = (float(lon_text), float(lat_text))
        except (TypeError, ValueError):
            continue
        points.append(NHCForecastPoint(valid_at=valid_at, center=center))
    unique_points = sorted({(point.valid_at, point.center) for point in points}, key=lambda item: item[0])
    return [NHCForecastPoint(valid_at=valid_at, center=center) for valid_at, center in unique_points]


def _parse_dbase_records(payload: bytes) -> list[dict[str, str]]:
    """Small DBF reader for NHC's published shapefile attribute table.

    Keeping this local avoids introducing a GDAL/GeoPandas dependency into the
    request path just to read forecast point attributes.
    """
    if len(payload) < 33:
        return []
    record_count = struct.unpack_from("<I", payload, 4)[0]
    header_length = struct.unpack_from("<H", payload, 8)[0]
    record_length = struct.unpack_from("<H", payload, 10)[0]
    fields: list[tuple[str, int]] = []
    offset = 32
    while offset + 32 <= len(payload) and payload[offset] != 0x0D:
        name = payload[offset : offset + 11].split(b"\x00", 1)[0].decode("latin-1").strip()
        size = payload[offset + 16]
        if not name or not size:
            return []
        fields.append((name.upper(), size))
        offset += 32
    if not fields or header_length + record_count * record_length > len(payload) + record_length:
        return []

    records: list[dict[str, str]] = []
    for index in range(record_count):
        start = header_length + index * record_length
        row = payload[start : start + record_length]
        if len(row) != record_length or row[:1] == b"*":
            continue
        cursor = 1
        record: dict[str, str] = {}
        for name, size in fields:
            record[name] = row[cursor : cursor + size].decode("latin-1", errors="ignore").strip()
            cursor += size
        records.append(record)
    return records


def _parse_point_shapes(payload: bytes) -> list[tuple[float, float] | None]:
    if len(payload) < 100:
        return []
    points: list[tuple[float, float] | None] = []
    offset = 100
    while offset + 12 <= len(payload):
        content_words = struct.unpack_from(">I", payload, offset + 4)[0]
        content_end = offset + 8 + content_words * 2
        if content_end > len(payload) or content_words < 2:
            break
        shape_type = struct.unpack_from("<I", payload, offset + 8)[0]
        if shape_type in {1, 11, 21} and content_end >= offset + 28:
            points.append(struct.unpack_from("<dd", payload, offset + 12))
        else:
            points.append(None)
        offset = content_end
    return points


def _parse_polygon_shapes(payload: bytes) -> list[list[list[tuple[float, float]]] | None]:
    """Read Polygon records from a small NHC forecast-radii shapefile.

    NHC distributes the official wind radii as ordinary WGS84 polygons.  The
    compact reader keeps a heavy GIS runtime out of the API request path.
    """
    if len(payload) < 100:
        return []
    polygons: list[list[list[tuple[float, float]]] | None] = []
    offset = 100
    while offset + 12 <= len(payload):
        content_words = struct.unpack_from(">I", payload, offset + 4)[0]
        content_end = offset + 8 + content_words * 2
        if content_end > len(payload) or content_words < 2:
            break
        content = offset + 8
        shape_type = struct.unpack_from("<I", payload, content)[0]
        if shape_type != 5 or content_end < content + 44:
            polygons.append(None)
            offset = content_end
            continue
        part_count = struct.unpack_from("<I", payload, content + 36)[0]
        point_count = struct.unpack_from("<I", payload, content + 40)[0]
        part_offset = content + 44
        point_offset = part_offset + 4 * part_count
        if not part_count or point_offset + 16 * point_count > content_end:
            polygons.append(None)
            offset = content_end
            continue
        part_indexes = list(struct.unpack_from(f"<{part_count}I", payload, part_offset))
        points = [struct.unpack_from("<dd", payload, point_offset + 16 * index) for index in range(point_count)]
        rings: list[list[tuple[float, float]]] = []
        for index, start in enumerate(part_indexes):
            end = part_indexes[index + 1] if index + 1 < len(part_indexes) else point_count
            ring = list(points[start:end])
            if len(ring) >= 3:
                if ring[0] != ring[-1]:
                    ring.append(ring[0])
                rings.append(ring)
        polygons.append(rings or None)
        offset = content_end
    return polygons


def parse_nhc_forecast_wind_radii(payload: bytes, minimum_knots: int = 34) -> list[dict]:
    """Return NHC's published forecast-wind-radius polygons as GeoJSON.

    This is a forecast exposure footprint, not an observed wind field and not
    a probability surface.  Only the requested official radius is returned.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = archive.namelist()
            dbf_name = next(name for name in names if "forecastradii" in name.lower() and name.lower().endswith(".dbf"))
            base = dbf_name.rsplit(".", 1)[0]
            shp_name = next(name for name in names if name.rsplit(".", 1)[0] == base and name.lower().endswith(".shp"))
            records = _parse_dbase_records(archive.read(dbf_name))
            polygons = _parse_polygon_shapes(archive.read(shp_name))
    except (OSError, StopIteration, zipfile.BadZipFile):
        return []

    features: list[dict] = []
    for record, rings in zip(records, polygons, strict=False):
        try:
            radius = int(float(record.get("RADII", "")))
        except ValueError:
            continue
        if radius != minimum_knots or not rings:
            continue
        features.append({
            "type": "Feature",
            "properties": {"wind_radius_knots": radius, "valid_time": record.get("VALIDTIME"), "storm_id": record.get("STORMID")},
            "geometry": {"type": "Polygon", "coordinates": [[[lon, lat] for lon, lat in ring] for ring in rings]},
        })
    return features


async def fetch_nhc_forecast_wind_radii(track: NHCForecastTrack, minimum_knots: int = 34) -> list[dict]:
    if not track.wind_field_url:
        return []
    payload = await safe_get_bytes(track.wind_field_url)
    return parse_nhc_forecast_wind_radii(payload, minimum_knots) if payload else []


def _point_time(record: dict[str, str], observed_at: datetime | None) -> datetime | None:
    period_text = record.get("FCSTPRD") or record.get("FORECASTHR") or record.get("TAU")
    try:
        period_hours = float(period_text) if period_text else None
    except ValueError:
        period_hours = None
    valid_at = _as_utc(record.get("VALIDTIME"))
    if valid_at:
        return valid_at
    if period_hours is None or not observed_at:
        return None
    date_text = record.get("ADVDATE") or record.get("ADVISDATE") or record.get("ADVDATETIME")
    advisory_at = _as_utc(date_text)
    if advisory_at and len((date_text or "").strip()) == 8:
        advisory_at = advisory_at.replace(hour=observed_at.hour, minute=0, second=0, microsecond=0)
    return (advisory_at or observed_at) + timedelta(hours=period_hours)


def _parse_shapefile_forecast_points(payload: bytes, observed_at: datetime | None) -> list[NHCForecastPoint]:
    """Extract the official point records and their FCSTPRD lead times."""
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = archive.namelist()
            candidate_names = sorted(
                (name for name in names if name.lower().endswith(".dbf")),
                key=lambda name: ("_pts" not in name.lower(), name),
            )
            records: list[dict[str, str]] = []
            points: list[tuple[float, float] | None] = []
            for dbf_name in candidate_names:
                candidate_records = _parse_dbase_records(archive.read(dbf_name))
                base = dbf_name.rsplit(".", 1)[0]
                shp_name = next(
                    (name for name in names if name.rsplit(".", 1)[0] == base and name.lower().endswith(".shp")),
                    None,
                )
                if not shp_name or not candidate_records or "FCSTPRD" not in candidate_records[0]:
                    continue
                candidate_points = _parse_point_shapes(archive.read(shp_name))
                if candidate_points:
                    records, points = candidate_records, candidate_points
                    break
    except (OSError, StopIteration, zipfile.BadZipFile):
        return []

    forecast_points: list[NHCForecastPoint] = []
    for record, center in zip(records, points, strict=False):
        valid_at = _point_time(record, observed_at)
        if center and valid_at:
            forecast_points.append(NHCForecastPoint(valid_at=valid_at, center=center))
    unique_points = sorted({(point.valid_at, point.center) for point in forecast_points}, key=lambda item: item[0])
    return [NHCForecastPoint(valid_at=valid_at, center=center) for valid_at, center in unique_points]


async def fetch_nhc_forecast_tracks(*, force: bool = False) -> AdapterResponse[NHCForecastTrack]:
    """Fetch presently issued NHC five-day forecast tracks for active storms."""
    global _cache
    now = time.monotonic()
    if not force and _cache and now - _cache[0] < _CACHE_TTL_SECONDS:
        return _cache[1]

    feed_payloads = await _fetch_basin_feeds()
    if not feed_payloads:
        return AdapterResponse(
            source_name="National Hurricane Center",
            status=DataStatus.UNAVAILABLE,
            note="Official NHC forecast feeds are currently unavailable; no substitute future events are shown.",
        )

    tracks = [track for basin, payload in feed_payloads for track in _parse_feed(payload, basin)]
    for track in tracks:
        shape_product = await safe_get_bytes(track.shape_url) if track.shape_url else None
        if shape_product:
            track.points = _parse_shapefile_forecast_points(shape_product, track.observed_at)
        if not track.points:
            product = await safe_get_bytes(track.track_url)
            if product:
                track.points = _parse_track_points(product)

    response = AdapterResponse(
        source_name="National Hurricane Center",
        status=DataStatus.LIVE,
        items=tracks,
        note=(
            "Official NHC active-storm forecast tracks for the Atlantic and eastern Pacific basins. "
            "No all-hazard or whole-world prediction is implied."
        ),
    )
    _cache = (now, response)
    return response


async def _fetch_basin_feeds() -> list[tuple[str, bytes]]:
    results: list[tuple[str, bytes]] = []
    for basin, url in _BASINS.items():
        payload = await safe_get_bytes(url)
        if payload:
            results.append((basin, payload))
    return results
