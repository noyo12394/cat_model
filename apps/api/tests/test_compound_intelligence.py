from app.schemas.enums import CertaintyClass, DataStatus
from app.services.compound_intelligence import build_compound_events


def test_compound_event_is_explicitly_demo(repo):
    events = build_compound_events(repo)
    assert len(events) == 1
    event = events[0]
    assert event.is_demo is True
    assert event.data_status == DataStatus.DEMO
    assert all(signal.data_status == DataStatus.DEMO for signal in event.signals)


def test_compound_event_separates_observed_forecast_and_inferred(repo):
    event = build_compound_events(repo)[0]
    certainty = {step.certainty for step in event.consequence_chain}
    assert CertaintyClass.OBSERVED in certainty
    assert CertaintyClass.FORECAST in certainty
    assert CertaintyClass.AI_INFERRED in certainty


def test_compound_event_exposes_evidence_gaps_and_next_checks(repo):
    event = build_compound_events(repo)[0]
    assert any(channel.agreement == "unavailable" for channel in event.evidence_agreement)
    assert [item.rank for item in event.next_checks] == [1, 2, 3]
    assert all(future.distinguishing_signal for future in event.possible_futures)
