"""Aggregate geometric review findings; not a safety certification."""
from gasgis.topology import endpoint_clusters
from gasgis.crossings import crossing_candidates
from gasgis.node_connectivity import match_nodes


def audit_network(parts, segments, nodes=(), tolerance_m=0.05):
    parts = list(parts)
    nodes = list(nodes)
    _, loose = endpoint_clusters(parts, tolerance_m)
    issues = [dict(issue='LOOSE_END', asset=str(a), related=str(e), x=p[0], y=p[1]) for a, e, p in loose]
    for crossing in crossing_candidates(segments):
        issues.append(dict(issue='CROSSING', asset=str(crossing['first']), related=str(crossing['second']), x=crossing['x'], y=crossing['y']))
    if nodes:
        endpoints = []
        for asset, start, end in parts:
            endpoints.extend([(asset, 0, *start), (asset, 1, *end)])
        _, unmatched = match_nodes(endpoints, nodes, tolerance_m)
        for item in unmatched:
            issues.append(dict(issue='NO_NEARBY_NODE', asset=str(item['pipe']), related=str(item['end']), x=item['x'], y=item['y']))
    return issues
