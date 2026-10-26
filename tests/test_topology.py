from gasgis.topology import endpoint_clusters


def test_connected_lines():
    clusters, loose = endpoint_clusters([
        ("A", (0, 0), (1, 0)),
        ("B", (1.02, 0), (2, 0)),
    ], tolerance_m=0.05)
    assert len(clusters) == 3
    assert len(loose) == 2


def test_disconnected_lines():
    _, loose = endpoint_clusters([
        ("A", (0, 0), (1, 0)),
        ("B", (3, 0), (4, 0)),
    ])
    assert len(loose) == 4


def test_no_segments():
    assert endpoint_clusters([]) == ([], [])
