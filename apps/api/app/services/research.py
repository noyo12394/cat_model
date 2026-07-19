"""Research & formula-discovery service (section 12).

This provides a *curated demonstration index* of well-known public technical
references plus a search/reformulate/rank pipeline. It deliberately does NOT:

* fabricate DOIs, URLs or metrics (unverified bibliographic details are marked
  as such rather than invented);
* extract equations from paywalled or unavailable text; or
* promote any discovered formula into the calculation engine — extraction only
  opens a human review task (section 12's non-negotiable review workflow).

A production build swaps ``CURATED_INDEX`` for live adapters over OpenAlex,
Crossref, arXiv and Semantic Scholar behind the same response shape.
"""

from __future__ import annotations

from app.schemas.research import (
    ExtractionRequestResult,
    PaperRecord,
    PaperSummary,
    ResearchSearchResponse,
    ReviewStatus,
    SourceStatus,
)

_VERIFY = "Demonstration index entry: verify authors, year, DOI and URL against the publisher before citing."

# Well-known, genuinely public technical references. Bibliographic details are
# intentionally conservative (doi/url left null) and flagged for verification;
# nothing here is a fabricated citation.
CURATED_INDEX: list[PaperRecord] = [
    PaperRecord(
        paper_id="fema-hazus-flood-tm",
        title="Hazus Flood Model Technical Manual",
        authors=["FEMA", "National Institute of Building Sciences"],
        year=None, publisher="U.S. Federal Emergency Management Agency (FEMA)",
        doi=None, source_url=None, peer_review_status="government_technical",
        hazard="flood", geography="United States", asset_type="buildings (multiple occupancies)",
        intensity_measure="flood depth", dependent_variable="damage ratio",
        model_type="depth-damage lookup", calibration_range="see manual by occupancy",
        validation_method="documented in manual",
        limitations=["Depth-damage relationships are generic by occupancy", "Not a substitute for site survey"],
        prohibited_extrapolations="Do not apply outside documented occupancy classes or depth ranges.",
        license_note="U.S. government technical manual; confirm current edition and terms.",
        extraction_performed=False, extraction_confidence="none",
        human_review_status=ReviewStatus.DISCOVERED, verification_note=_VERIFY,
    ),
    PaperRecord(
        paper_id="usace-egm-residential-depth-damage",
        title="Generic Depth-Damage Relationships for Residential Structures (Economic Guidance Memorandum)",
        authors=["U.S. Army Corps of Engineers"],
        year=None, publisher="U.S. Army Corps of Engineers (USACE)",
        doi=None, source_url=None, peer_review_status="government_technical",
        hazard="flood", geography="United States", asset_type="residential buildings",
        intensity_measure="flood depth above first floor", dependent_variable="percent damage",
        model_type="depth-damage curve", calibration_range="documented in the memorandum",
        validation_method="expert-elicited / survey based",
        limitations=["Generic national curves", "First-floor elevation strongly affects results"],
        prohibited_extrapolations="Do not apply residential curves to commercial or industrial occupancy.",
        license_note="U.S. government guidance; confirm current memorandum number and edition.",
        extraction_performed=False, extraction_confidence="none",
        human_review_status=ReviewStatus.DISCOVERED, verification_note=_VERIFY,
    ),
    PaperRecord(
        paper_id="usace-egm-nonresidential-depth-damage",
        title="Generic Depth-Damage Relationships for Non-Residential Structures (Economic Guidance Memorandum)",
        authors=["U.S. Army Corps of Engineers"],
        year=None, publisher="U.S. Army Corps of Engineers (USACE)",
        doi=None, source_url=None, peer_review_status="government_technical",
        hazard="flood", geography="United States", asset_type="commercial and industrial buildings",
        intensity_measure="flood depth above first floor", dependent_variable="percent damage",
        model_type="depth-damage curve", calibration_range="documented in the memorandum",
        validation_method="expert-elicited / survey based",
        limitations=["Generic by broad occupancy category", "Contents damage handled separately"],
        prohibited_extrapolations="Do not apply non-residential curves to residential occupancy.",
        license_note="U.S. government guidance; confirm current memorandum number and edition.",
        extraction_performed=False, extraction_confidence="none",
        human_review_status=ReviewStatus.DISCOVERED, verification_note=_VERIFY,
    ),
    PaperRecord(
        paper_id="hazus-flood-loss-methodology",
        title="HAZUS-MH Flood Loss Estimation Methodology",
        authors=["Scawthorn, C.", "and others"],
        year=None, publisher="Natural Hazards Review (ASCE)",
        doi=None, source_url=None, peer_review_status="peer_reviewed",
        hazard="flood", geography="United States", asset_type="buildings and contents",
        intensity_measure="flood depth", dependent_variable="direct economic loss",
        model_type="methodology / depth-damage integration", calibration_range="see publication",
        validation_method="described in publication",
        limitations=["Methodology paper; parameters live in the technical manuals", "Verify edition and authors"],
        prohibited_extrapolations="Do not treat the summary as sufficient to implement equations without the manual.",
        license_note="Peer-reviewed publication; obtain through a licensed library, do not store paywalled text.",
        extraction_performed=False, extraction_confidence="none",
        human_review_status=ReviewStatus.DISCOVERED, verification_note=_VERIFY,
    ),
]

_INDEX_BY_ID = {p.paper_id: p for p in CURATED_INDEX}

_SOURCE_STATUS = [
    SourceStatus(source="OpenAlex", status="unavailable", note="Live adapter not configured in this demonstration."),
    SourceStatus(source="Crossref", status="unavailable", note="Live adapter not configured in this demonstration."),
    SourceStatus(source="arXiv", status="unavailable", note="Live adapter not configured in this demonstration."),
    SourceStatus(source="Semantic Scholar", status="unavailable", note="Live adapter not configured in this demonstration."),
    SourceStatus(source="RiskChain curated index", status="demo_index", note="Curated public technical references; verify before citing."),
]

_STOPWORDS = {"the", "a", "an", "for", "of", "in", "and", "to", "find", "show", "me", "with", "on", "buildings", "building"}


def reformulate(query: str, hazard: str | None, asset_type: str | None) -> list[str]:
    terms = {w for w in query.lower().replace(",", " ").split() if w not in _STOPWORDS and len(w) > 2}
    if hazard:
        terms.add(hazard.lower())
    if asset_type:
        terms.add(asset_type.lower())
    # A couple of domain synonyms to broaden recall.
    if "vulnerability" in terms or "damage" in terms:
        terms.update({"depth-damage", "fragility"})
    return sorted(terms)


def _relevance(paper: PaperRecord, terms: list[str], hazard: str | None, asset_type: str | None) -> float:
    haystack = " ".join([
        paper.title.lower(), paper.hazard, paper.asset_type, paper.intensity_measure,
        paper.model_type, paper.geography.lower(),
    ])
    score = sum(1.0 for t in terms if t in haystack)
    if hazard and hazard.lower() == paper.hazard:
        score += 2.0
    if asset_type and asset_type.lower() in paper.asset_type:
        score += 1.5
    if paper.peer_review_status in ("peer_reviewed", "government_technical"):
        score += 0.5
    denom = max(1.0, len(terms) + 4.0)
    return round(min(1.0, score / denom), 3)


def search(query: str, hazard: str | None = None, asset_type: str | None = None) -> ResearchSearchResponse:
    terms = reformulate(query, hazard, asset_type)
    scored = [(p, _relevance(p, terms, hazard, asset_type)) for p in CURATED_INDEX]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    results = [
        PaperSummary(
            paper_id=p.paper_id, title=p.title, publisher=p.publisher, year=p.year,
            hazard=p.hazard, asset_type=p.asset_type, relevance=rel,
            peer_review_status=p.peer_review_status, human_review_status=p.human_review_status,
        )
        for p, rel in scored if rel > 0
    ]
    return ResearchSearchResponse(
        query=query,
        reformulated_terms=terms,
        results=results,
        source_status=_SOURCE_STATUS,
        notice=(
            "Results come from a curated demonstration index of public technical references. "
            "Live academic-source adapters are the production path. An abstract is never sufficient "
            "to implement an equation, and no formula is added to the engine without human review."
        ),
    )


def get_paper(paper_id: str) -> PaperRecord | None:
    return _INDEX_BY_ID.get(paper_id)


EXTRACTION_WORKFLOW = [
    "Relevant passage and equation extracted (only from legally available text)",
    "Units and variables parsed",
    "Applicability checked",
    "Independent implementation created",
    "Unit and dimensional tests",
    "Published examples reproduced",
    "Sensitivity and monotonicity tests",
    "Human model review",
    "Approved model-registry entry",
]


def request_extraction(paper_id: str) -> ExtractionRequestResult | None:
    paper = _INDEX_BY_ID.get(paper_id)
    if paper is None:
        return None
    return ExtractionRequestResult(
        paper_id=paper_id,
        accepted=True,
        new_status=ReviewStatus.UNDER_REVIEW,
        workflow=EXTRACTION_WORKFLOW,
        message=(
            "Extraction opens a human-review task; it does not implement or promote any formula. "
            "Full-text extraction requires legally available source text and is not performed automatically. "
            "A formula reaches the engine only via the model registry after review."
        ),
    )
