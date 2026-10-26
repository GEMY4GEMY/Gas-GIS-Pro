"""Read line endpoints and identify disconnected gas network ends."""
from qgis.core import QgsWkbTypes
from gasgis.topology import endpoint_clusters


def disconnected_endpoints(layer, tolerance_m=0.05):
    if not layer.isValid() or layer.geometryType() != QgsWkbTypes.LineGeometry:
        raise ValueError("Select a valid line layer")
    if not layer.crs().isValid() or layer.crs().isGeographic():
        raise ValueError("A projected CRS is required")
    units = layer.crs().mapUnits()
    from qgis.core import QgsUnitTypes
    if units != QgsUnitTypes.DistanceMeters:
        raise ValueError("Layer CRS must use meters")
    segments = []
    for feature in layer.getFeatures():
        geometry = feature.geometry()
        if geometry.isNull() or geometry.isEmpty():
            continue
        lines = geometry.asMultiPolyline() if geometry.isMultipart() else [geometry.asPolyline()]
        for part, line in enumerate(lines):
            if len(line) < 2:
                continue
            segments.append((f"{feature.id()}:{part}", (line[0].x(), line[0].y()),
                             (line[-1].x(), line[-1].y())))
    _, loose = endpoint_clusters(segments, tolerance_m)
    return [{"asset": asset, "end": end, "x": xy[0], "y": xy[1]} for asset, end, xy in loose]
