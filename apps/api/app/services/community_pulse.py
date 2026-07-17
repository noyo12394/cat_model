"""Community Pulse: deterministic sentiment analysis over community reports.

This service turns a set of short, categorized community reports into a
transparent picture of public concern for an incident. It is a demonstration
built on seeded reports, and it follows the platform's hard rules:

* The concern index is a **weighted count** of categorical sentiment tags, not
  a number produced by a language model. The weights and band thresholds are
  module-level constants so the calculation is inspectable and reproducible.
* Every report is ``user_reported`` or ``unverified`` and is cross-checked
  against confirmed conditions so rumor can be separated from corroborated
  signal, rather than silently blended into "the data".

If real community-report ingestion is connected later, only ``_demo_reports``
changes; the aggregation below stays identical.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from app.db.memory_repository import MemoryRepository
from app.schemas.community_pulse import (
    CommunityPulseResponse,
    CommunityReport,
    ConcernIndex,
    CorroborationSummary,
    SentimentBucket,
    ThemeCluster,
)
from app.schemas.enums import CertaintyClass, DataStatus

# Concern contribution of each sentiment tag. Explicit and inspectable so the
# concern index can never be mistaken for a model-invented number.
SENTIMENT_WEIGHT: dict[str, float] = {
    "alarmed": 1.0,
    "concerned": 0.65,
    "seeking_info": 0.45,
    "calm": 0.15,
    "relieved": 0.0,
}

SENTIMENT_LABEL: dict[str, str] = {
    "alarmed": "Alarmed",
    "concerned": "Concerned",
    "seeking_info": "Seeking information",
    "calm": "Calm / reassuring",
    "relieved": "Relieved",
}

THEME_LABEL: dict[str, str] = {
    "access": "Roads & river crossings",
    "power": "Power & utilities",
    "water_level": "Water level sightings",
    "evacuation": "Evacuation & shelter",
    "assistance": "Requests for help",
    "rumor": "Unverified rumor",
}

# Concern index band thresholds (applied to the 0..1 weighted score).
BAND_THRESHOLDS: list[tuple[float, str, str]] = [
    (0.70, "alarmed", "Alarmed"),
    (0.50, "concerned", "Concerned"),
    (0.30, "watchful", "Watchful"),
    (0.0, "calm", "Calm"),
]

TREND_EPSILON = 0.08


def _demo_reports(now: datetime) -> list[CommunityReport]:
    """Seeded, categorized community reports for the Bethlehem flood demo.

    Tags (sentiment/theme/corroboration) are the *inputs* to the aggregation.
    In a live system these would come from a moderated ingestion + classifier
    pipeline; here they are fixed so the demo is reproducible.
    """

    def at(minutes_ago: int) -> datetime:
        return now - timedelta(minutes=minutes_ago)

    return [
        CommunityReport(
            report_id="cr-01",
            posted_at=at(112),
            channel="Community app",
            text="Water's coming up fast under the Hill-to-Hill approach, wasn't like this an hour ago.",
            location_label="Hill-to-Hill Bridge, Bethlehem",
            center=(-75.3746, 40.6220),
            sentiment="concerned",
            theme="water_level",
            certainty=CertaintyClass.USER_REPORTED,
            corroboration="corroborated",
            corroboration_detail="Direction matches the rising USGS demo gauge trend on the Monocacy.",
        ),
        CommunityReport(
            report_id="cr-02",
            posted_at=at(96),
            channel="Public social post",
            text="Is the Fahy Bridge closed? Need to get to St. Luke's and don't want to get stuck.",
            location_label="South Bethlehem",
            center=(-75.3660, 40.6180),
            sentiment="seeking_info",
            theme="access",
            certainty=CertaintyClass.UNVERIFIED,
            corroboration="uncorroborated",
            corroboration_detail="No official closure is confirmed for the Fahy Bridge in this demo.",
        ),
        CommunityReport(
            report_id="cr-03",
            posted_at=at(78),
            channel="Public social post",
            text="Heard the whole south side is being evacuated tonight.",
            location_label="South Bethlehem",
            center=(-75.3705, 40.6150),
            sentiment="alarmed",
            theme="rumor",
            certainty=CertaintyClass.UNVERIFIED,
            corroboration="conflicts",
            corroboration_detail="No evacuation order exists in this demo; flagged as unverified rumor.",
        ),
        CommunityReport(
            report_id="cr-04",
            posted_at=at(64),
            channel="Community app",
            text="Basement flooding on our street near the creek, water still rising.",
            location_label="Monocacy Creek neighborhood",
            center=(-75.3790, 40.6270),
            sentiment="concerned",
            theme="water_level",
            certainty=CertaintyClass.USER_REPORTED,
            corroboration="corroborated",
            corroboration_detail="Consistent with the seeded heavy-rain warning footprint.",
        ),
        CommunityReport(
            report_id="cr-05",
            posted_at=at(58),
            channel="Info hotline",
            text="Power flickered twice, anyone else near Elm St lose it?",
            location_label="North Bethlehem",
            center=(-75.3760, 40.6320),
            sentiment="seeking_info",
            theme="power",
            certainty=CertaintyClass.UNVERIFIED,
            corroboration="uncorroborated",
            corroboration_detail="No utility outage feed is connected in this demo.",
        ),
        CommunityReport(
            report_id="cr-06",
            posted_at=at(44),
            channel="Community app",
            text="Roads look fine on the north side, just heavy rain. Don't panic.",
            location_label="North Bethlehem",
            center=(-75.3700, 40.6350),
            sentiment="calm",
            theme="access",
            certainty=CertaintyClass.USER_REPORTED,
            corroboration="uncorroborated",
            corroboration_detail="Local observation; no independent confirmation attached.",
        ),
        CommunityReport(
            report_id="cr-07",
            posted_at=at(33),
            channel="Public social post",
            text="Low approach to the bridge is under water now, turn around.",
            location_label="Hill-to-Hill Bridge, Bethlehem",
            center=(-75.3744, 40.6215),
            sentiment="alarmed",
            theme="access",
            certainty=CertaintyClass.USER_REPORTED,
            corroboration="corroborated",
            corroboration_detail="Matches the forecast boundary overlapping the low approach.",
        ),
        CommunityReport(
            report_id="cr-08",
            posted_at=at(24),
            channel="Info hotline",
            text="Elderly neighbor on the south side may need help getting out if it gets worse.",
            location_label="South Bethlehem",
            center=(-75.3680, 40.6165),
            sentiment="concerned",
            theme="assistance",
            certainty=CertaintyClass.USER_REPORTED,
            corroboration="uncorroborated",
            corroboration_detail="Assistance request; would be routed to responders, not auto-verified.",
        ),
        CommunityReport(
            report_id="cr-09",
            posted_at=at(15),
            channel="Public social post",
            text="Where do we go if they open a shelter? Nobody's said anything official.",
            location_label="South Bethlehem",
            center=(-75.3690, 40.6172),
            sentiment="seeking_info",
            theme="evacuation",
            certainty=CertaintyClass.UNVERIFIED,
            corroboration="uncorroborated",
            corroboration_detail="No shelter has been announced in this demo.",
        ),
        CommunityReport(
            report_id="cr-10",
            posted_at=at(8),
            channel="Community app",
            text="Second crossing still passable but water's close to the road edge.",
            location_label="Fahy Bridge, Bethlehem",
            center=(-75.3660, 40.6182),
            sentiment="concerned",
            theme="access",
            certainty=CertaintyClass.USER_REPORTED,
            corroboration="corroborated",
            corroboration_detail="Consistent with elevated-but-passable route status in the demo.",
        ),
        CommunityReport(
            report_id="cr-11",
            posted_at=at(4),
            channel="Public social post",
            text="This is a dam break, get out now!!",
            location_label="Bethlehem",
            center=(-75.3705, 40.6259),
            sentiment="alarmed",
            theme="rumor",
            certainty=CertaintyClass.UNVERIFIED,
            corroboration="conflicts",
            corroboration_detail="No dam-failure signal exists; flagged as high-alarm unverified rumor.",
        ),
    ]


def _concern_band(score: float) -> tuple[str, str]:
    for threshold, band, label in BAND_THRESHOLDS:
        if score >= threshold:
            return band, label
    return "calm", "Calm"


def _concern_index(reports: list[CommunityReport]) -> ConcernIndex:
    if not reports:
        return ConcernIndex(
            score=0.0,
            band="calm",
            band_label="Calm",
            trend="steady",
            trend_detail="No community reports in this window.",
            method="No reports to aggregate.",
        )

    def weighted(subset: list[CommunityReport]) -> float:
        if not subset:
            return 0.0
        return sum(SENTIMENT_WEIGHT.get(r.sentiment, 0.4) for r in subset) / len(subset)

    ordered = sorted(reports, key=lambda r: r.posted_at)
    score = round(weighted(ordered), 3)
    band, band_label = _concern_band(score)

    midpoint = len(ordered) // 2
    earlier = weighted(ordered[:midpoint])
    later = weighted(ordered[midpoint:])
    delta = later - earlier
    if delta > TREND_EPSILON:
        trend, trend_detail = "rising", "More recent reports skew more concerned than earlier ones."
    elif delta < -TREND_EPSILON:
        trend, trend_detail = "easing", "More recent reports skew calmer than earlier ones."
    else:
        trend, trend_detail = "steady", "Concern is holding roughly level across the window."

    return ConcernIndex(
        score=score,
        band=band,
        band_label=band_label,
        trend=trend,
        trend_detail=trend_detail,
        method=(
            "Weighted count of categorical sentiment tags "
            "(alarmed 1.0, concerned 0.65, seeking-info 0.45, calm 0.15, relieved 0.0), "
            "averaged over all reports. No language model produces this number."
        ),
    )


def _sentiment_breakdown(reports: list[CommunityReport]) -> list[SentimentBucket]:
    total = len(reports) or 1
    counts = Counter(r.sentiment for r in reports)
    order = ["alarmed", "concerned", "seeking_info", "calm", "relieved"]
    buckets = [
        SentimentBucket(
            sentiment=sentiment,
            label=SENTIMENT_LABEL.get(sentiment, sentiment),
            count=counts.get(sentiment, 0),
            share=round(counts.get(sentiment, 0) / total, 3),
        )
        for sentiment in order
        if counts.get(sentiment, 0) > 0
    ]
    return buckets


def _theme_clusters(reports: list[CommunityReport]) -> list[ThemeCluster]:
    clusters: list[ThemeCluster] = []
    by_theme: dict[str, list[CommunityReport]] = {}
    for report in reports:
        by_theme.setdefault(report.theme, []).append(report)

    for theme, group in by_theme.items():
        dominant = Counter(r.sentiment for r in group).most_common(1)[0][0]
        corr = Counter(r.corroboration for r in group)
        if corr.get("conflicts"):
            corr_note = f"{corr['conflicts']} report(s) conflict with confirmed conditions - treat as rumor."
        elif corr.get("corroborated"):
            corr_note = f"{corr['corroborated']} report(s) line up with confirmed conditions."
        else:
            corr_note = "No independent confirmation attached yet."
        clusters.append(
            ThemeCluster(
                theme=theme,
                label=THEME_LABEL.get(theme, theme.replace("_", " ").title()),
                count=len(group),
                dominant_sentiment=dominant,
                example=group[0].text,
                corroboration_note=corr_note,
            )
        )
    clusters.sort(key=lambda c: c.count, reverse=True)
    return clusters


def build_community_pulse(
    repo: MemoryRepository,
    incident_id: str = "developing-flood-bethlehem",
) -> CommunityPulseResponse:
    now = datetime.now(timezone.utc)
    incident = repo.get_incident(incident_id, mode="live")
    reports = _demo_reports(now)

    corr_counts = Counter(r.corroboration for r in reports)
    corroboration = CorroborationSummary(
        corroborated=corr_counts.get("corroborated", 0),
        uncorroborated=corr_counts.get("uncorroborated", 0),
        conflicts=corr_counts.get("conflicts", 0),
        note=(
            "Corroborated reports align with confirmed demo conditions; conflicting reports "
            "are surfaced as rumor to watch, never hidden or blended into the totals."
        ),
    )

    return CommunityPulseResponse(
        incident_id=incident_id,
        region_label=incident.region_label if incident else "Bethlehem, Pennsylvania",
        window_label="Community reports, last ~2 hours (demo)",
        generated_at=now,
        data_status=DataStatus.DEMO,
        is_demo=True,
        total_reports=len(reports),
        concern_index=_concern_index(reports),
        sentiment_breakdown=_sentiment_breakdown(reports),
        theme_clusters=_theme_clusters(reports),
        corroboration=corroboration,
        reports=sorted(reports, key=lambda r: r.posted_at, reverse=True),
        limitations=[
            "These are seeded demonstration reports, not live community signals.",
            "Sentiment and theme tags are categorical inputs; a real deployment needs a moderated, "
            "auditable classifier, not an unconstrained language model.",
            "Community mood is a supporting signal only - it never overrides official warnings or sensors.",
            "Report volume reflects who is online and posting, not the true distribution of people affected.",
        ],
        responsible_use=[
            "Do not use community reports to identify, target, or take action against individuals.",
            "Route assistance requests to responders through approved channels; this view does not dispatch help.",
            "Unverified and conflicting reports are labeled as such and must be confirmed before acting.",
        ],
    )
