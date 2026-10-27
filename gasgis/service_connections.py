"""Geometry-only service connection proposals; not a construction design approval."""
from math import hypot


def nearest_point_on_segment(point, start, end):
    """Return nearest XY point on a finite segment and its Euclidean distance."""
    px, py = point
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    t = 0.0 if length_sq == 0 else max(
        0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq)
    )
    foot = (ax + t * dx, ay + t * dy)
    return foot, hypot(px - foot[0], py - foot[1])


def propose_service_connection(riser, main_segments, max_distance_m=5.0):
    """Propose shortest straight segment from a riser to an existing main.

    Coordinates must be in a shared projected CRS whose map units are meters.
    This does not check obstacles, crossings, rights of way or gas safety rules.
    """
    if max_distance_m < 0:
        raise ValueError("Maximum distance cannot be negative")
    best = None
    for index, segment in enumerate(main_segments):
        foot, distance = nearest_point_on_segment(riser, segment[0], segment[1])
        if best is None or distance < best["distance_m"]:
            best = {
                "riser": tuple(riser),
                "main_point": foot,
                "distance_m": distance,
                "segment_index": index,
            }
    if best is None:
        return None
    best["within_limit"] = best["distance_m"] <= max_distance_m
    return best
