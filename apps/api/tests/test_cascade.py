from app.services.cascade import run_cascade


def test_directly_exposed_node_has_zero_hops(repo):
    result = run_cascade(repo, hazard_facility_ids=["fac-hill-to-hill-bridge"])
    exposed = next(n for n in result.nodes if n.facility_id == "fac-hill-to-hill-bridge")
    assert exposed.directly_exposed is True
    assert exposed.hops_from_hazard == 0


def test_downstream_hospital_is_reachable_within_a_few_hops(repo):
    result = run_cascade(repo, hazard_facility_ids=["fac-hill-to-hill-bridge"])
    hospital = next(n for n in result.nodes if n.facility_id == "fac-stlukes-bethlehem")
    assert hospital.hops_from_hazard is not None
    assert hospital.hops_from_hazard >= 1
    assert hospital.estimated_minutes_to_consequence == hospital.hops_from_hazard * 25.0


def test_removing_a_node_drops_it_from_active_propagation(repo):
    result = run_cascade(
        repo, hazard_facility_ids=["fac-hill-to-hill-bridge"], removed_facility_ids=["fac-hill-to-hill-bridge"]
    )
    removed_node = next(n for n in result.nodes if n.facility_id == "fac-hill-to-hill-bridge")
    assert removed_node.is_removed is True
    assert all(n.hops_from_hazard is None for n in result.nodes if n.facility_id != "fac-hill-to-hill-bridge")


def test_unaffected_node_has_no_hop_distance(repo):
    result = run_cascade(repo, hazard_facility_ids=["fac-hill-to-hill-bridge"])
    university = next(n for n in result.nodes if n.facility_id == "place-lehigh-university")
    # University provides_access_to the bridge, so it IS reachable in this
    # graph; assert the more meaningful invariant instead: a facility with no
    # path at all (e.g. a gauge with only an upstream_of edge to another
    # gauge) is None.
    monocacy_gauge = next(n for n in result.nodes if n.facility_id == "fac-gauge-monocacy")
    assert monocacy_gauge.hops_from_hazard is None
    assert university.hops_from_hazard is not None
