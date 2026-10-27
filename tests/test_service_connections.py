import pytest

from gasgis.service_connections import (
    nearest_point_on_segment,
    propose_service_connection,
)


def test_nearest_point_on_segment():
    point, distance = nearest_point_on_segment((3, 4), (0, 0), (10, 0))
    assert point == (3, 0)
    assert distance == 4


def test_nearest_endpoint_for_outside_projection():
    point, distance = nearest_point_on_segment((12, 0), (0, 0), (10, 0))
    assert point == (10, 0)
    assert distance == 2


def test_service_proposal_chooses_closest_main():
    proposal = propose_service_connection(
        (3, 4), [((0, 20), (10, 20)), ((0, 0), (10, 0))]
    )
    assert proposal["segment_index"] == 1
    assert proposal["main_point"] == (3, 0)
    assert proposal["distance_m"] == 4
    assert proposal["within_limit"]


def test_out_of_range_proposal_is_flagged():
    proposal = propose_service_connection(
        (3, 6), [((0, 0), (10, 0))], max_distance_m=5
    )
    assert proposal["within_limit"] is False


def test_empty_mains_and_negative_limit():
    assert propose_service_connection((0, 0), []) is None
    with pytest.raises(ValueError):
        propose_service_connection((0, 0), [], -1)


def test_degenerate_main_segment():
    proposal = propose_service_connection((3, 4), [((0, 0), (0, 0))])
    assert proposal["distance_m"] == 5
    assert proposal["within_limit"]
