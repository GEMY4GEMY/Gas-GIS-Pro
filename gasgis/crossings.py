"""Small-scale 2D segment intersection diagnostics.

Intersections may represent crossings without physical junctions.
"""


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def segment_intersection(a, b, c, d, epsilon=1e-10):
    """Return an interior intersection coordinate or None.

    Collinear overlaps are intentionally excluded pending separate review.
    """
    r = (b[0] - a[0], b[1] - a[1])
    s = (d[0] - c[0], d[1] - c[1])
    denominator = _cross(r, s)
    if abs(denominator) <= epsilon:
        return None
    q = (c[0] - a[0], c[1] - a[1])
    t = _cross(q, s) / denominator
    u = _cross(q, r) / denominator
    if epsilon < t < 1 - epsilon and epsilon < u < 1 - epsilon:
        return (a[0] + t * r[0], a[1] + t * r[1])
    return None


def crossing_candidates(segments):
    """Find interior crossings among (id, start, end) segments."""
    segments = list(segments)
    findings = []
    for i, (first_id, a, b) in enumerate(segments):
        for second_id, c, d in segments[i + 1:]:
            point = segment_intersection(a, b, c, d)
            if point is not None:
                findings.append({
                    "first": first_id, "second": second_id,
                    "x": point[0], "y": point[1]
                })
    return findings
