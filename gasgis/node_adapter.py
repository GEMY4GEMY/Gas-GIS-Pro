"""Extract valve and riser coordinates for pipe endpoint checks."""
from qgis.core import QgsWkbTypes, QgsUnitTypes


def point_nodes(layer, target_crs):
    if not layer.isValid() or layer.geometryType() != QgsWkbTypes.PointGeometry:
        raise ValueError("Select a valid point layer")
    if layer.crs() != target_crs:
        raise ValueError("Point and pipe layers must have the same CRS")
    if not layer.crs().isValid() or layer.crs().isGeographic():
        raise ValueError("Projected metric CRS required")
    if layer.crs().mapUnits() != QgsUnitTypes.DistanceMeters:
        raise ValueError("CRS must use meters")
    nodes = []
    for feature in layer.getFeatures():
        geometry = feature.geometry()
        if geometry.isNull() or geometry.isEmpty():
            continue
        points = geometry.asMultiPoint() if geometry.isMultipart() else [geometry.asPoint()]
        for i, point in enumerate(points):
            nodes.append((f"{feature.id()}:{i}", point.x(), point.y()))
    return nodes
