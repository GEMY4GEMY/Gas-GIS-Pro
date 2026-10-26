"""Planar, metric network connectivity diagnostics.

Coordinates must be in the same projected CRS, in meters.
This module does not infer gas pressure or flow.
"""
from math import hypot


def distance(a, b):
    return hypot(a[0] - b[0], a[1] - b[1])


def endpoint_clusters(segments, tolerance_m=0.05):
    """Return endpoint clusters and disconnected endpoints.

    segments: iterable of (asset_id, start_xy, end_xy). This is O(n²)
    and intended for small prototype datasets.
    """
    if tolerance_m < 0:
        raise ValueError("Tolerance must be non-negative")
    endpoints = []
    for asset_id, start, end in segments:
        if distance(start, end) <= 0:
            raise ValueError(f"Zero-length segment: {asset_id}")
        endpoints.extend([(asset_id, 0, tuple(start)), (asset_id, 1, tuple(end))])
    parent = list(range(len(endpoints)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(endpoints)):
        for j in range(i + 1, len(endpoints)):
            if distance(endpoints[i][2], endpoints[j][2]) <= tolerance_m:
                a, b = root(i), root(j)
                if a != b:
                    parent[b] = a

    groups = {}
    for i, endpoint in enumerate(endpoints):
        groups.setdefault(root(i), []).append(endpoint)
    disconnected = [
        members[0] for members in groups.values()
        if len({item[0] for item in members}) == 1
    ]
    return list(groups.values()), disconnected
