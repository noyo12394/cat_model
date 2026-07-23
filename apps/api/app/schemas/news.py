"""Source-linked live news metadata. Headlines are evidence leads, not facts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.enums import DataStatus


class NewsArticle(BaseModel):
    article_id: str
    title: str
    url: HttpUrl
    publisher_domain: str
    source_country: str | None = None
    language: str | None = None
    published_at: datetime


class NewsArticlesResponse(BaseModel):
    articles: list[NewsArticle] = Field(default_factory=list)
    data_status: DataStatus
    retrieved_at: datetime
    query_label: str
    hazard_filter: str
    hours: int
    source_name: str = "GDELT DOC 2.0 Article List"
    source_url: HttpUrl = "https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/"
    notice: str = (
        "News headlines are publisher-reported leads, not verified observations, "
        "official alerts, model inputs, or loss estimates. Open the original source "
        "and corroborate before acting."
    )
    error: str | None = None
