"""Build a traceable community-signal view from a selected official event."""

from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterResponse
from app.adapters.x_community import CommunityPost
from app.schemas.community_signals import CommunitySignal, CommunitySignalsResponse
from app.schemas.enums import DataStatus
from app.schemas.global_event import GlobalEvent


def build_community_signals(
    event: GlobalEvent,
    source: AdapterResponse[CommunityPost],
    *,
    now: datetime | None = None,
) -> CommunitySignalsResponse:
    now = now or datetime.now(timezone.utc)
    if source.status == DataStatus.UNAVAILABLE:
        return CommunitySignalsResponse(
            event_id=event.event_id,
            event_name=event.name,
            event_center=event.center,
            availability="unavailable",
            availability_label="Verified community source unavailable",
            availability_detail=source.note or "No community-source result is available, so no substitute sentiment or reports are shown.",
            generated_at=now,
            data_status=DataStatus.UNAVAILABLE,
            error=source.note,
        )
    signals = [
        CommunitySignal(
            post_id=post.post_id,
            text=post.text,
            observed_at=post.created_at,
            language=post.language,
            tone=post.tone,  # type: ignore[arg-type]
            report_type=post.report_type,  # type: ignore[arg-type]
            tags=post.tags,
            source_url=post.source_url,
        )
        for post in source.items
    ]
    detail = (
        f"{len(signals)} recent public post{'s' if len(signals) != 1 else ''} matched the selected official event query. "
        "Every item remains unverified and is held outside the hazard score."
        if signals else "No public recent posts matched the selected official event query."
    )
    return CommunitySignalsResponse(
        event_id=event.event_id,
        event_name=event.name,
        event_center=event.center,
        availability="available",
        availability_label="Live community reports" if signals else "No matching recent community reports",
        availability_detail=detail,
        generated_at=now,
        data_status=source.status,
        items=signals,
    )


def unavailable_community_signals(event_id: str, detail: str, *, now: datetime | None = None) -> CommunitySignalsResponse:
    return CommunitySignalsResponse(
        event_id=event_id,
        event_name="Selected event",
        event_center=(0.0, 0.0),
        availability="unavailable",
        availability_label="Community signals unavailable",
        availability_detail=detail,
        generated_at=now or datetime.now(timezone.utc),
        data_status=DataStatus.UNAVAILABLE,
        error=detail,
    )
