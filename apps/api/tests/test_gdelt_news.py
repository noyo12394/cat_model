from __future__ import annotations

import pytest

from app.adapters import gdelt_news
from app.core.config import Settings
from app.schemas.enums import DataStatus


@pytest.mark.asyncio
async def test_gdelt_news_keeps_only_source_metadata(monkeypatch):
    async def fake_get_json(url, params=None, headers=None, **kwargs):
        assert params["mode"] == "artlist"
        assert params["format"] == "json"
        return {"articles": [{
            "url": "https://example.com/report",
            "title": "  Flooding reported in example region  ",
            "seendate": "20260723T193000Z",
            "domain": "example.com",
            "language": "English",
            "sourcecountry": "United States",
        }]}

    monkeypatch.setattr(gdelt_news, "safe_get_json", fake_get_json)
    gdelt_news._cache.clear()
    response = await gdelt_news.fetch_disaster_news(Settings(), force=True)
    assert response.status == DataStatus.LIVE
    assert len(response.items) == 1
    assert response.items[0].title == "Flooding reported in example region"
    assert response.items[0].publisher_domain == "example.com"


@pytest.mark.asyncio
async def test_gdelt_news_outage_is_not_replaced_with_mock_articles(monkeypatch):
    async def fake_get_json(url, params=None, headers=None, **kwargs):
        return None

    monkeypatch.setattr(gdelt_news, "safe_get_json", fake_get_json)
    gdelt_news._cache.clear()
    response = await gdelt_news.fetch_disaster_news(Settings(), force=True)
    assert response.status == DataStatus.UNAVAILABLE
    assert response.items == []
