from app.services.geo import haversine_km, point_in_polygon, segment_intersects_polygon

SQUARE = [[(-75.4, 40.6), (-75.3, 40.6), (-75.3, 40.7), (-75.4, 40.7), (-75.4, 40.6)]]


def test_haversine_zero_distance():
    assert haversine_km((-75.0, 40.0), (-75.0, 40.0)) == 0.0


def test_haversine_known_distance_order_of_magnitude():
    # Bethlehem, PA to Philadelphia, PA is roughly 75-80 km as the crow
    # flies (not exact - a geodesic sanity check, not a survey-grade
    # assertion).
    dist = haversine_km((-75.3705, 40.6259), (-75.1652, 39.9526))
    assert 65 < dist < 90


def test_point_in_polygon_inside():
    assert point_in_polygon((-75.35, 40.65), SQUARE) is True


def test_point_in_polygon_outside():
    assert point_in_polygon((-75.0, 40.65), SQUARE) is False


def test_segment_intersects_polygon_true_when_endpoint_inside():
    assert segment_intersects_polygon((-75.5, 40.65), (-75.35, 40.65), SQUARE) is True


def test_segment_intersects_polygon_false_when_entirely_outside():
    assert segment_intersects_polygon((-75.0, 40.0), (-75.05, 40.05), SQUARE) is False
