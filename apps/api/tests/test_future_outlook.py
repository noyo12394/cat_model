from __future__ import annotations

import io
import zipfile
from datetime import datetime, timedelta, timezone

from app.adapters.base import AdapterResponse
from app.adapters.nhc import NHCForecastPoint, NHCForecastTrack, _parse_feed, _parse_track_points, _point_time
from app.schemas.enums import DataStatus
from app.services.future_outlook import build_future_outlook


def test_nhc_feed_and_kmz_parser_keep_only_timestamped_forecast_points():
    feed = b"""<?xml version=\"1.0\"?>
    <rss xmlns:nhc=\"https://www.nhc.noaa.gov\"><channel>
      <item><title>Summary - Tropical Storm Elida (EP5/EP052026)</title><link>https://www.nhc.noaa.gov/text/advisory</link><pubDate>Thu, 16 Jul 2026 20:33:13 GMT</pubDate><nhc:Cyclone><nhc:type>Tropical Storm</nhc:type><nhc:name>Elida</nhc:name><nhc:atcf>EP052026</nhc:atcf><nhc:headline>Expected to turn northwest.</nhc:headline></nhc:Cyclone></item>
      <item><title>Advisory #009 Forecast Track [kmz] - Tropical Storm Elida (EP5/EP052026)</title><link>https://www.nhc.noaa.gov/storm_graphics/api/EP052026_009adv_TRACK.kmz</link></item>
    </channel></rss>"""
    track = _parse_feed(feed, "Eastern Pacific")[0]
    assert track.name == "Elida"
    assert track.track_url.endswith("TRACK.kmz")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "track.kml",
            """<kml xmlns=\"http://www.opengis.net/kml/2.2\"><Document>
              <Placemark><TimeStamp><when>2026-07-17T12:00:00Z</when></TimeStamp><Point><coordinates>-119.0,16.0,0</coordinates></Point></Placemark>
              <Placemark><Point><coordinates>-118.3,15.8,0</coordinates></Point></Placemark>
            </Document></kml>""",
        )
    points = _parse_track_points(buffer.getvalue())
    assert points == [NHCForecastPoint(datetime(2026, 7, 17, 12, tzinfo=timezone.utc), (-119.0, 16.0))]
    assert _point_time({"VALIDTIME": "2026-07-17 11:00 AM Fri PDT"}, None) == datetime(2026, 7, 17, 18, tzinfo=timezone.utc)


def test_future_date_returns_only_a_published_track_point_or_an_explicit_unavailable_state():
    now = datetime(2026, 7, 16, 18, tzinfo=timezone.utc)
    track = NHCForecastTrack(
        event_id="NHC-EP052026",
        name="Elida",
        storm_type="Tropical Storm",
        basin="Eastern Pacific",
        observed_at=now,
        headline="Expected to turn northwest.",
        advisory_url="https://www.nhc.noaa.gov/text/advisory",
        track_url="https://www.nhc.noaa.gov/storm_graphics/api/EP052026_009adv_TRACK.kmz",
        points=[
            NHCForecastPoint(now + timedelta(hours=12), (-119.0, 16.0)),
            NHCForecastPoint(now + timedelta(hours=36), (-121.0, 17.5)),
        ],
    )
    source = AdapterResponse(source_name="National Hurricane Center", status=DataStatus.LIVE, items=[track])

    supported = build_future_outlook(now + timedelta(hours=24), source, now=now)
    assert supported.availability == "available"
    assert supported.items[0].name == "Elida"
    assert supported.items[0].selected_point_center == (-119.0, 16.0)
    assert supported.items[0].coverage_status == "dated_track_point"
    assert supported.items[0].certainty_class == "official_forecast"

    advisory_only = build_future_outlook(now + timedelta(hours=96), source, now=now)
    assert advisory_only.items[0].coverage_status == "official_advisory"
    assert advisory_only.items[0].selected_point_center is None

    unsupported = build_future_outlook(now + timedelta(days=30), source, now=now)
    assert unsupported.availability == "unavailable"
    assert not unsupported.items
    assert "does not extrapolate" in unsupported.availability_detail
