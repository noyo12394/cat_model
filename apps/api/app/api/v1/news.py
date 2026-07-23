"""Live publisher-linked news metadata, intentionally separate from alerts."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.adapters.gdelt_news import fetch_disaster_news
from app.api.deps import settings_dep
from app.core.config import Settings
from app.schemas.news import NewsArticlesResponse

router = APIRouter(prefix="/news", tags=["news"])

NewsHazard = Literal["all", "flood", "wildfire", "earthquake", "storm", "drought", "cat_model", "resilience"]


@router.get("/articles", response_model=NewsArticlesResponse)
async def get_news_articles(
    hazard: NewsHazard = "all",
    hours: int = Query(default=24, ge=1, le=168),
    force: bool = Query(default=False, description="Bypass the short server cache for an explicit user refresh."),
    settings: Settings = Depends(settings_dep),
) -> NewsArticlesResponse:
    response = await fetch_disaster_news(settings, hazard=hazard, hours=hours, force=force)
    return NewsArticlesResponse(
        articles=response.items,
        data_status=response.status,
        retrieved_at=response.retrieved_at,
        query_label={
            "all": "Global hazards, catastrophe modelling and resilience",
            "flood": "Flooding",
            "wildfire": "Wildfire",
            "earthquake": "Earthquake and tsunami",
            "storm": "Storm and wind",
            "drought": "Drought and heat",
            "cat_model": "Catastrophe modelling",
            "resilience": "Disaster resilience and adaptation",
        }[hazard],
        hazard_filter=hazard,
        hours=hours,
        source_name=response.source_name,
        source_url=response.source_url or "https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/",
        notice=(
            "Article records are published headline leads, not verified observations, official alerts, model inputs, or loss estimates. "
            "Open the original source and corroborate before acting."
            if response.status.value == "live" and response.source_name == "GDELT DOC 2.0 Article List"
            else response.note or "News records are source-linked reading leads, not hazard measurements or model outputs."
        ),
        error=response.note if response.status.value == "unavailable" else None,
    )
