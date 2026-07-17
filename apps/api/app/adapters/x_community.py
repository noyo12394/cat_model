"""Read-only community posts from the official X recent-search API.

This adapter is deliberately opt-in.  It never scrapes, never makes a demo
feed, and does not claim that a post is a verified on-the-ground observation.
The downstream service uses deterministic language labels so a generative model
cannot invent a crisis signal from community text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.adapters.base import AdapterResponse, safe_get_json
from app.core.config import Settings
from app.schemas.enums import DataStatus
from app.schemas.global_event import GlobalEvent

X_DOCS_URL = "https://docs.x.com/x-api/posts/search-recent-posts"


@dataclass(frozen=True)
class CommunityPost:
    post_id: str
    text: str
    created_at: datetime
    language: str | None
    tone: str
    report_type: str
    tags: list[str]
    source_url: str


async def fetch_x_community_posts(event: GlobalEvent, settings: Settings) -> AdapterResponse[CommunityPost]:
    """Fetch only recent public posts explicitly matching the selected event.

    Geographic location is not inferred from a profile, author, or text. Posts
    are instead shown as unverified reports linked to the active GDACS event.
    """
    if not settings.x_bearer_token:
        return AdapterResponse(
            source_name="X API",
            status=DataStatus.UNAVAILABLE,
            note="X_BEARER_TOKEN is not configured; no community posts or synthetic sentiment are shown.",
        )
    query = _event_query(event)
    payload = await safe_get_json(
        f"{settings.x_api_base_url.rstrip('/')}/tweets/search/recent",
        {
            "query": query,
            "max_results": 25,
            "tweet.fields": "created_at,lang",
        },
        headers={"Authorization": f"Bearer {settings.x_bearer_token}"},
    )
    if not isinstance(payload, dict):
        return AdapterResponse(
            source_name="X API",
            status=DataStatus.UNAVAILABLE,
            note="The X recent-search source could not be reached. No substitute community signal is used.",
        )
    raw_posts = payload.get("data")
    if not isinstance(raw_posts, list):
        return AdapterResponse(source_name="X API", status=DataStatus.LIVE, note="No public recent posts matched the selected official event query.")
    posts: list[CommunityPost] = []
    for raw in raw_posts:
        post = _parse_post(raw)
        if post is not None:
            posts.append(post)
    return AdapterResponse(source_name="X API", status=DataStatus.LIVE, items=posts)


def _event_query(event: GlobalEvent) -> str:
    # Use source-issued event words and country, not an unrestricted free-text
    # search field. This keeps the tab tied to a current official event.
    event_name = _quoted_query_term(event.name)
    country = _quoted_query_term(event.country)
    return f"{event_name} {country} -is:retweet"


def _quoted_query_term(value: str) -> str:
    normalized = " ".join(value.replace('"', " ").split())[:120]
    return f'"{normalized}"' if " " in normalized else normalized


def _parse_post(raw: Any) -> CommunityPost | None:
    if not isinstance(raw, dict):
        return None
    post_id = raw.get("id")
    text = raw.get("text")
    created_at = raw.get("created_at")
    if not isinstance(post_id, str) or not isinstance(text, str) or not isinstance(created_at, str):
        return None
    try:
        observed_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    clean_text = " ".join(text.split())[:500]
    tone, report_type, tags = classify_community_language(clean_text)
    return CommunityPost(
        post_id=post_id,
        text=clean_text,
        created_at=observed_at,
        language=raw.get("lang") if isinstance(raw.get("lang"), str) else None,
        tone=tone,
        report_type=report_type,
        tags=tags,
        source_url=f"https://x.com/i/web/status/{post_id}",
    )


def classify_community_language(text: str) -> tuple[str, str, list[str]]:
    """Transparent lexical labels; labels are not fact verification or sentiment scores."""
    normalized = text.lower()
    tags = [label for label, pattern in _TAG_PATTERNS if re.search(pattern, normalized)]
    if re.search(r"\b(help|trapped|evacuate|evacuation|rescue|emergency)\b", normalized):
        tone = "urgent_language"
    elif tags or re.search(r"\b(worried|concern|scared|danger)\b", normalized):
        tone = "concern_language"
    else:
        tone = "neutral_language"
    if re.search(r"\b(road|bridge|street).{0,28}\b(closed|blocked|washed out)\b|\b(power|electricity).{0,28}\b(out|down)\b", normalized):
        report_type = "possible_impact_report"
    elif re.search(r"\b(flooded|smoke|ash|shaking|rainfall|wind|fire)\b", normalized):
        report_type = "possible_condition_report"
    else:
        report_type = "event_mention"
    return tone, report_type, tags[:4]


_TAG_PATTERNS: list[tuple[str, str]] = [
    ("flooding", r"\b(flood|flooded|inundat)"),
    ("road access", r"\b(road|bridge|street|highway|route).{0,28}\b(closed|blocked|washed out|impassable)\b"),
    ("power", r"\b(power outage|electricity.{0,18}\b(out|down)|blackout)\b"),
    ("smoke", r"\b(smoke|air quality|ash)\b"),
    ("fire", r"\b(fire|wildfire|burning)\b"),
    ("seismic", r"\b(earthquake|quake|shaking|aftershock)\b"),
]
