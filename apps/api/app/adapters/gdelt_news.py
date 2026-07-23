"""GDELT DOC 2.0 article-index adapter for the live News workspace.

The adapter intentionally preserves only source metadata. It does not scrape
publisher pages, summarize articles, assign impact scores, or turn headlines
into catastrophe-model inputs.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone

from app.adapters.base import AdapterResponse, safe_get_json
from app.core.config import Settings
from app.schemas.enums import DataStatus
from app.schemas.news import NewsArticle

_CACHE_TTL_SECONDS = 300
_MAX_ARTICLES = 50
_cache: dict[tuple[str, int], tuple[float, AdapterResponse[NewsArticle]]] = {}

_QUERIES: dict[str, tuple[str, str]] = {
    "all": (
        '(earthquake OR wildfire OR flood OR hurricane OR cyclone OR "tropical storm" OR landslide OR tsunami OR drought)',
        "Major natural hazards",
    ),
    "flood": ('(flood OR "flash flood" OR inundation)', "Flooding"),
    "wildfire": ('(wildfire OR "forest fire" OR bushfire)', "Wildfire"),
    "earthquake": ('(earthquake OR aftershock OR tsunami)', "Earthquake and tsunami"),
    "storm": ('(hurricane OR cyclone OR typhoon OR "tropical storm" OR tornado OR "severe weather")', "Storm and wind"),
    "drought": ('(drought OR "extreme heat" OR heatwave)', "Drought and heat"),
}


def _published_at(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _article_from_raw(item: object) -> NewsArticle | None:
    if not isinstance(item, dict):
        return None
    url = item.get("url")
    title = item.get("title")
    published_at = _published_at(item.get("seendate"))
    if not isinstance(url, str) or not url.startswith(("http://", "https://")) or not isinstance(title, str) or not title.strip() or published_at is None:
        return None
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    return NewsArticle(
        article_id=f"gdelt-{digest}",
        title=" ".join(title.split()),
        url=url,
        publisher_domain=str(item.get("domain") or "Publisher not reported"),
        source_country=str(item["sourcecountry"]) if item.get("sourcecountry") else None,
        language=str(item["language"]) if item.get("language") else None,
        published_at=published_at,
    )


async def fetch_disaster_news(
    settings: Settings,
    *,
    hazard: str = "all",
    hours: int = 24,
    force: bool = False,
) -> AdapterResponse[NewsArticle]:
    """Return recent, source-linked article metadata from the public GDELT index."""
    normalized_hazard = hazard if hazard in _QUERIES else "all"
    normalized_hours = min(max(int(hours), 1), 168)
    cache_key = (normalized_hazard, normalized_hours)
    now = time.monotonic()
    if not force and cache_key in _cache and now - _cache[cache_key][0] < _CACHE_TTL_SECONDS:
        return _cache[cache_key][1]

    query, query_label = _QUERIES[normalized_hazard]
    payload = await safe_get_json(
        settings.gdelt_doc_base_url,
        params={
            "query": query,
            "mode": "artlist",
            "format": "json",
            "sort": "datedesc",
            "timespan": f"{normalized_hours}h",
            "maxrecords": _MAX_ARTICLES,
        },
        timeout=15.0,
    )
    raw_articles = payload.get("articles") if isinstance(payload, dict) else None
    if not isinstance(raw_articles, list):
        return AdapterResponse(
            source_name="GDELT DOC 2.0 Article List",
            status=DataStatus.UNAVAILABLE,
            items=[],
            note="The GDELT article index is unavailable. No substitute headlines are shown.",
        )

    by_url: dict[str, NewsArticle] = {}
    for raw_article in raw_articles:
        article = _article_from_raw(raw_article)
        if article is not None:
            by_url[str(article.url)] = article
    result = AdapterResponse(
        source_name="GDELT DOC 2.0 Article List",
        status=DataStatus.LIVE,
        items=sorted(by_url.values(), key=lambda article: article.published_at, reverse=True),
        note=f"{len(by_url)} publisher-linked article records returned for {query_label.lower()}.",
    )
    _cache[cache_key] = (now, result)
    return result
