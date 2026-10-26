"""Read a gas line layer as individual straight segments for audit."""
from qgis.core import QgsWkbTypes, QgsUnitTypes


def line_segments(layer):
    if not layer.isValid() or layer.geometryType() != QgsWkbTypes.LineGeometry:
        raise ValueError("Select a valid line layer")
    if not layer.crs().isValid() or layer.crs().isGeographic():
        raise ValueError("A projected CRS is required")
    if layer.crs().mapUnits() != QgsUnitTypes.DistanceMeters:
        raise ValueError("Layer CRS must use meters")
    segments = []
    for feature in layer.getFeatures():
        geometry = feature.geometry()
        if geometry.isNull() or geometry.isEmpty():
            continue
        lines = geometry.asMultiPolyline() if geometry.isMultipart() else [geometry.asPolyline()]
        for part_no, line in enumerate(lines):
            for vertex_no in range(len(line) - 1):
                start, end = line[vertex_no], line[vertex_no + 1]
                if start == end:
                    continue
                segments.append((
                    f"{feature.id()}:{part_no}:{vertex_no}",
                    (start.x(), start.y()), (end.x(), end.y())
                ))
    return segments
