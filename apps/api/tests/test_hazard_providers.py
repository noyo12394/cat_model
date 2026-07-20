from __future__ import annotations

import pytest

from app.core.config import Settings
from app.services.cat import hazard_providers


@pytest.mark.asyncio
async def test_usgs_event_detail_uses_fdsn_for_regional_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_get(url: str, params: dict[str, str]) -> dict[str, object]:
        captured.update(url=url, params=params)
        return {"properties": {"title": "M 7.1 - Ridgecrest Earthquake Sequence", "products": {"shakemap": []}}}

    monkeypatch.setattr(hazard_providers, "safe_get_json", fake_get)
    provider = hazard_providers.USGSEarthquakeProvider(Settings())

    detail = await provider.get_event_details("ci38457511")

    assert captured["url"] == "https://earthquake.usgs.gov/fdsnws/event/1/query"
    assert captured["params"] == {"eventid": "ci38457511", "format": "geojson"}
    assert detail["properties"]["title"] == "M 7.1 - Ridgecrest Earthquake Sequence"
