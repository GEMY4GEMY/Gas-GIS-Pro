from gasgis.crossings import segment_intersection, crossing_candidates


def test_crossing():
    assert segment_intersection((0, 0), (2, 2), (0, 2), (2, 0)) == (1.0, 1.0)


def test_endpoint_touch_excluded():
    assert segment_intersection((0, 0), (1, 0), (1, 0), (2, 1)) is None


def test_crossing_candidates():
    results = crossing_candidates([
        ("P1", (0, 0), (2, 2)),
        ("P2", (0, 2), (2, 0)),
    ])
    assert len(results) == 1
    assert results[0]["first"] == "P1"
