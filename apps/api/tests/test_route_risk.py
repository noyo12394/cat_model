from app.services.route_risk import analyze_route


def test_lehigh_to_stlukes_returns_three_labeled_states(repo):
    options = analyze_route(repo, "lehigh-university", "fac-stlukes-bethlehem")
    levels = {o.exposure_level for o in options}
    assert levels == {"elevated", "lower", "unavailable"}


def test_no_route_is_ever_positively_labeled_safe(repo):
    """'safe' may appear only inside an explicit negation (e.g. 'not a
    guarantee of safe passage'), never as a bare positive claim like
    'this route is safe' (principle 2.5)."""
    options = analyze_route(repo, "lehigh-university", "fac-stlukes-bethlehem")
    for o in options:
        note = o.exposure_note.lower()
        assert "is safe" not in note
        assert "this route is safe" not in note


def test_hill_to_hill_route_overlaps_warning_geometry(repo):
    options = analyze_route(repo, "lehigh-university", "fac-stlukes-bethlehem")
    hill_to_hill = next(o for o in options if o.route_id == "route-a-hill-to-hill")
    assert hill_to_hill.exposure_level == "elevated"
    assert hill_to_hill.segments[0].hazard_overlap is True


def test_unknown_place_pair_returns_empty(repo):
    assert analyze_route(repo, "does-not-exist", "also-not-real") == []


def test_generic_pair_falls_back_to_low_confidence_estimate(repo):
    options = analyze_route(repo, "bethlehem-pa", "philadelphia-pa")
    assert len(options) == 1
    assert options[0].confidence == "low"
