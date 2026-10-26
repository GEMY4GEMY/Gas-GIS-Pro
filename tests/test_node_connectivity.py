from gasgis.node_connectivity import match_nodes


def test_nearby_node():
    matched, unmatched = match_nodes(
        [("P1", 0, 10.0, 20.0)],
        [("V1", 10.03, 20.0)], tolerance_m=0.05
    )
    assert len(matched) == 1
    assert matched[0]["node"] == "V1"
    assert unmatched == []


def test_missing_node():
    matched, unmatched = match_nodes(
        [("P1", 1, 10.0, 20.0)],
        [("V1", 11.0, 20.0)], tolerance_m=0.05
    )
    assert matched == []
    assert len(unmatched) == 1


def test_invalid_tolerance():
    try:
        match_nodes([], [], tolerance_m=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("Negative tolerance must fail")
