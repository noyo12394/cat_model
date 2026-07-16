from app.services.what_changed import compute_what_changed


def test_what_changed_reports_gauge_deltas_since_one_hour(repo):
    changed = compute_what_changed(repo, "developing-flood-bethlehem", "live", "1_hour")
    assert changed is not None
    labels = [c.label for c in changed.changes]
    assert any("increased" in label or "decreased" in label for label in labels)


def test_what_changed_since_yesterday_includes_full_timeline(repo):
    changed = compute_what_changed(repo, "developing-flood-bethlehem", "live", "yesterday")
    assert changed is not None
    assert len(changed.changes) >= 5


def test_what_changed_unknown_incident_returns_none(repo):
    assert compute_what_changed(repo, "does-not-exist", "live", "1_hour") is None


def test_what_changed_always_reports_closure_status(repo):
    changed = compute_what_changed(repo, "developing-flood-bethlehem", "live", "1_hour")
    assert any("closure" in c.label.lower() for c in changed.changes)
