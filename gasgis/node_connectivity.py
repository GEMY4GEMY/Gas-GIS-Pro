"""Endpoint-to-node proximity checks for gas network assets.

This does not assert physical connectivity; all inputs use projected meters.
"""
from math import hypot


def match_nodes(endpoints, nodes, tolerance_m=0.05):
    """Return matches and unmatched endpoints.

    endpoints: (pipe_id, end_no, x, y)
    nodes: (node_id, x, y)
    """
    if tolerance_m < 0:
        raise ValueError("Tolerance must be nonnegative")
    matches = []
    unmatched = []
    for pipe_id, end_no, x, y in endpoints:
        nearby = [
            (hypot(x - nx, y - ny), node_id)
            for node_id, nx, ny in nodes
            if hypot(x - nx, y - ny) <= tolerance_m
        ]
        if nearby:
            distance_m, node_id = min(nearby, key=lambda item: (item[0], str(item[1])))
            matches.append({
                "pipe": pipe_id, "end": end_no,
                "node": node_id, "distance_m": distance_m
            })
        else:
            unmatched.append({
                "pipe": pipe_id, "end": end_no, "x": x, "y": y
            })
    return matches, unmatched
