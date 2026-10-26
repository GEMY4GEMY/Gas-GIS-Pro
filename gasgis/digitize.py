"""Interactive digitizing tool for point and line vector layers.

Uses QGIS map canvas snapping configuration. Saving is explicit via toolbar.
"""
from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsWkbTypes
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand
from qgis.PyQt.QtCore import Qt


class GasDigitizeTool(QgsMapToolEmitPoint):
    def __init__(self, canvas, layer, on_feature_added=None):
        super().__init__(canvas)
        self.canvas = canvas
        self.layer = layer
        self.on_feature_added = on_feature_added
        self.vertices = []
        self.rubber = QgsRubberBand(canvas, QgsWkbTypes.LineGeometry)
        self.rubber.setWidth(2)

    def canvasReleaseEvent(self, event):
        if not self.layer.isEditable():
            return
        if event.button() == Qt.RightButton:
            self.finish_line()
            return
        if event.button() != Qt.LeftButton:
            return
        match = self.canvas.snappingUtils().snapToMap(event.pos())
        point = match.point() if match.isValid() else self.toMapCoordinates(event.pos())
        layer_point = self.canvas.mapSettings().mapToLayerCoordinates(self.layer, point)
        geometry_type = self.layer.geometryType()
        if geometry_type == QgsWkbTypes.PointGeometry:
            self.add_geometry(QgsGeometry.fromPointXY(QgsPointXY(layer_point)))
        elif geometry_type == QgsWkbTypes.LineGeometry:
            self.vertices.append(QgsPointXY(layer_point))
            self.rubber.addPoint(point)

    def finish_line(self):
        if len(self.vertices) >= 2:
            self.add_geometry(QgsGeometry.fromPolylineXY(self.vertices))
        self.vertices = []
        self.rubber.reset(QgsWkbTypes.LineGeometry)

    def add_geometry(self, geometry):
        feature = QgsFeature(self.layer.fields())
        feature.setGeometry(geometry)
        if not self.layer.addFeature(feature):
            raise RuntimeError("Failed to add geometry")
        self.layer.triggerRepaint()
        if self.on_feature_added:
            self.on_feature_added()

    def deactivate(self):
        self.vertices = []
        self.rubber.reset(QgsWkbTypes.LineGeometry)
        super().deactivate()
