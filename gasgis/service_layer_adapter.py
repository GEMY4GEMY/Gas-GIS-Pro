"""Read actual QGIS gas layers and propose service connections (no edits)."""
from qgis.core import QgsWkbTypes

from gasgis.geometry_adapter import line_segments, validate_line_layer
from gasgis.service_connections import propose_service_connection


def service_proposals(risers_layer, mains_layer, max_distance_m=5.0):
    """Return per-riser proposed service lines in a shared meter-based CRS.

    Proposals are geometry-only, not construction-ready or automatically saved.
    """
    validate_line_layer(mains_layer)
    if not risers_layer.isValid() or risers_layer.geometryType() != QgsWkbTypes.PointGeometry:
        raise ValueError("Select a valid point layer for risers")
    if risers_layer.crs() != mains_layer.crs():
        raise ValueError("Risers and mains must use the same projected CRS")
    segments = [
        (start, end) for _, start, end in line_segments(mains_layer)
    ]
    results = []
    for feature in risers_layer.getFeatures():
        geometry = feature.geometry()
        if geometry.isNull() or geometry.isEmpty():
            continue
        points = geometry.asMultiPoint() if geometry.isMultipart() else [geometry.asPoint()]
        for point in points:
            proposal = propose_service_connection(
                (point.x(), point.y()), segments, max_distance_m
            )
            if proposal is not None:
                results.append({"riser_feature_id": feature.id(), **proposal})
    return results
