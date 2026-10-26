"""Gas GIS Pro desktop GIS shell. Requires a working PyQGIS runtime."""
import sys
from pathlib import Path

from qgis.core import QgsApplication, QgsProject, QgsVectorLayer
from qgis.gui import QgsMapCanvas, QgsMapToolPan
from qgis.PyQt.QtCore import Qt
from gasgis.project_validation import validate_vector_path
from gasgis.asset_layers import create_asset_layer, SCHEMAS
from gasgis.editing import start_editing, save_edits, rollback_edits
from gasgis.digitize import GasDigitizeTool
from gasgis.network_audit import disconnected_endpoints
from gasgis.audit_export import export_audit_csv
from gasgis.geometry_adapter import line_segments, line_parts
from gasgis.unified_audit import audit_network
from gasgis.crossings import crossing_candidates
from gasgis.node_adapter import point_nodes
from gasgis.node_connectivity import match_nodes
from qgis.core import QgsGeometry, QgsPointXY, QgsFeature, QgsField
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsSnappingConfig, QgsWkbTypes
from qgis.PyQt.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QToolBar, QDockWidget,
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QInputDialog
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gas GIS Pro — Development")
        self.resize(1400, 850)
        self.project = QgsProject.instance()
        self.canvas = QgsMapCanvas()
        self.canvas.setCanvasColor(Qt.white)
        self.setCentralWidget(self.canvas)
        self.pan_tool = QgsMapToolPan(self.canvas)
        self.canvas.setMapTool(self.pan_tool)
        self.digitize_tool = None
        self.layer_visibility = {}

        self.layer_tree = QTreeWidget()
        self.layer_tree.setHeaderLabels(["Layers"])
        self.layer_tree.itemChanged.connect(self.set_layer_visibility)
        self.layer_tree.itemSelectionChanged.connect(self.update_attributes)
        layer_dock = QDockWidget("Layers", self)
        layer_dock.setWidget(self.layer_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, layer_dock)

        self.attributes = QTableWidget()
        self.attributes.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.attributes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        attr_dock = QDockWidget("Attributes (preview: first 500 features)", self)
        attr_dock.setWidget(self.attributes)
        self.addDockWidget(Qt.BottomDockWidgetArea, attr_dock)

        toolbar = QToolBar("GIS Tools")
        self.addToolBar(toolbar)
        for title, callback in (
            ("Open layer", self.open_layer),
            ("New gas layer", self.new_gas_layer),
            ("Start editing", self.start_selected_edit),
            ("Draw feature", self.draw_selected_feature),
            ("Audit pipe ends", self.audit_selected_layer),
            ("Audit crossings", self.audit_crossings),
            ("Audit valve/riser proximity", self.audit_nodes),
            ("Unified audit CSV", self.unified_audit_csv),
            ("Undo", self.undo_selected_edit),
            ("Redo", self.redo_selected_edit),
            ("Save edits", self.save_selected_edit),
            ("Discard edits", self.discard_selected_edit),
            ("Open project", self.open_project),
            ("Save project", self.save_project),
            ("Pan", lambda: self.canvas.setMapTool(self.pan_tool)),
            ("Zoom in", self.canvas.zoomIn),
            ("Zoom out", self.canvas.zoomOut),
            ("Zoom full", self.canvas.zoomToFullExtent),
        ):
            toolbar.addAction(title, callback)
        self.project.layersAdded.connect(lambda _: self.refresh_layers())
        self.project.layersRemoved.connect(lambda _: self.refresh_layers())
        self.statusBar().showMessage("Development build — not validated for production")

    def refresh_layers(self):
        layers = [layer for layer in self.project.mapLayers().values() if layer.isValid()]
        previous = self.layer_tree.currentItem()
        selected_id = previous.data(0, Qt.UserRole) if previous else None
        valid_ids = {layer.id() for layer in layers}
        self.layer_visibility = {
            key: value for key, value in self.layer_visibility.items()
            if key in valid_ids
        }
        self.layer_tree.blockSignals(True)
        self.layer_tree.clear()
        for layer in reversed(layers):
            item = QTreeWidgetItem([layer.name()])
            item.setData(0, Qt.UserRole, layer.id())
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Checked if self.layer_visibility.get(layer.id(), True) else Qt.Unchecked)
            self.layer_tree.addTopLevelItem(item)
            if layer.id() == selected_id:
                self.layer_tree.setCurrentItem(item)
        self.layer_tree.blockSignals(False)
        self.sync_canvas_layers()
        self.update_attributes()

    def sync_canvas_layers(self):
        visible = []
        for i in range(self.layer_tree.topLevelItemCount()):
            item = self.layer_tree.topLevelItem(i)
            layer = self.project.mapLayer(item.data(0, Qt.UserRole))
            if layer and item.checkState(0) == Qt.Checked:
                visible.append(layer)
        self.canvas.setLayers(visible)
        self.canvas.refresh()

    def set_layer_visibility(self, item, column):
        self.layer_visibility[item.data(0, Qt.UserRole)] = (
            item.checkState(0) == Qt.Checked
        )
        self.sync_canvas_layers()

    def update_attributes(self):
        self.attributes.clear()
        self.attributes.setRowCount(0)
        self.attributes.setColumnCount(0)
        item = self.layer_tree.currentItem()
        if not item:
            return
        layer = self.project.mapLayer(item.data(0, Qt.UserRole))
        if not isinstance(layer, QgsVectorLayer):
            return
        fields = [field.name() for field in layer.fields()]
        self.attributes.setColumnCount(len(fields))
        self.attributes.setHorizontalHeaderLabels(fields)
        for row, feature in enumerate(layer.getFeatures()):
            if row >= 500:
                break
            self.attributes.insertRow(row)
            for col, value in enumerate(feature.attributes()):
                self.attributes.setItem(row, col, QTableWidgetItem(str(value)))

    def open_layer(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open vector layer", "",
            "Vector files (*.shp *.gpkg *.geojson *.json *.dxf);;All files (*)"
        )
        if not path:
            return
        errors = validate_vector_path(path)
        if errors:
            QMessageBox.warning(self, "Input check failed", ", ".join(errors))
            return
        layer = QgsVectorLayer(path, Path(path).stem, "ogr")
        if not layer.isValid():
            QMessageBox.warning(self, "Import failed", "Unable to load the layer.")
            return
        self.project.addMapLayer(layer)
        self.canvas.zoomToFullExtent()

    def new_gas_layer(self):
        layer_name, ok = QInputDialog.getItem(
            self, "Gas asset layer", "Asset type:", list(SCHEMAS), 0, False
        )
        if not ok:
            return
        crs, ok = QInputDialog.getText(
            self, "Projected CRS", "EPSG code (e.g. EPSG:32636):"
        )
        if not ok:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "New gas GeoPackage", "", "GeoPackage (*.gpkg)"
        )
        if not path:
            return
        try:
            layer = create_asset_layer(path, layer_name, crs.strip())
        except (ValueError, FileExistsError, FileNotFoundError, RuntimeError) as exc:
            QMessageBox.warning(self, "Create layer failed", str(exc))
            return
        self.project.addMapLayer(layer)
        self.statusBar().showMessage(f"Created {layer_name} in {path}", 10000)

    def selected_vector_layer(self):
        item = self.layer_tree.currentItem()
        if item is None:
            raise ValueError("Select a layer in the Layers panel first")
        layer = self.project.mapLayer(item.data(0, Qt.UserRole))
        if not isinstance(layer, QgsVectorLayer):
            raise ValueError("Select a vector layer")
        return layer

    def run_edit_action(self, operation):
        if self.digitize_tool is not None:
            self.canvas.setMapTool(self.pan_tool)
            self.digitize_tool = None
        try:
            operation(self.selected_vector_layer())
            self.update_attributes()
            self.canvas.refresh()
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Editing", str(exc))

    def draw_selected_feature(self):
        try:
            layer = self.selected_vector_layer()
            if not layer.isEditable():
                raise ValueError("Start editing before drawing")
            if layer.geometryType() not in (
                QgsWkbTypes.PointGeometry, QgsWkbTypes.LineGeometry
            ):
                raise ValueError("Drawing supports point and line layers only")
            config = self.project.snappingConfig()
            config.setEnabled(True)
            config.setMode(QgsSnappingConfig.AllLayers)
            config.setType(QgsSnappingConfig.Vertex)
            config.setTolerance(12)
            config.setUnits(QgsSnappingConfig.Pixels)
            self.project.setSnappingConfig(config)
            self.digitize_tool = GasDigitizeTool(
                self.canvas, layer, on_feature_added=self.update_attributes
            )
            self.canvas.setMapTool(self.digitize_tool)
            self.statusBar().showMessage(
                "Left click to draw; right click to finish a line. Save edits to commit."
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Digitizing", str(exc))

    def undo_selected_edit(self):
        try:
            layer = self.selected_vector_layer()
            if not layer.isEditable():
                raise ValueError("Start editing first")
            layer.undoStack().undo()
            self.canvas.refresh()
            self.update_attributes()
        except ValueError as exc:
            QMessageBox.warning(self, "Undo", str(exc))

    def redo_selected_edit(self):
        try:
            layer = self.selected_vector_layer()
            if not layer.isEditable():
                raise ValueError("Start editing first")
            layer.undoStack().redo()
            self.canvas.refresh()
            self.update_attributes()
        except ValueError as exc:
            QMessageBox.warning(self, "Redo", str(exc))

    def audit_selected_layer(self):
        try:
            layer = self.selected_vector_layer()
            findings = disconnected_endpoints(layer)
            if not findings:
                QMessageBox.information(self, "Network audit", "No loose pipe ends detected.")
                return
            from qgis.core import QgsCoordinateReferenceSystem
            markers = QgsVectorLayer(
                "Point?crs=" + layer.crs().authid(), "AUDIT - loose endpoints", "memory"
            )
            markers.dataProvider().addAttributes([
                QgsField("asset", QVariant.String),
                QgsField("end_no", QVariant.Int),
            ])
            markers.updateFields()
            features = []
            for finding in findings:
                feature = QgsFeature(markers.fields())
                feature.setGeometry(QgsGeometry.fromPointXY(
                    QgsPointXY(finding["x"], finding["y"])
                ))
                feature.setAttributes([finding["asset"], finding["end"]])
                features.append(feature)
            report_path, _ = QFileDialog.getSaveFileName(
                self, 'Save audit CSV (optional)', '', 'CSV (*.csv)'
            )
            if report_path:
                if not report_path.lower().endswith('.csv'):
                    report_path += '.csv'
                export_audit_csv(findings, report_path)
            markers.dataProvider().addFeatures(features)
            markers.updateExtents()
            self.project.addMapLayer(markers)
            self.canvas.zoomToFullExtent()
            QMessageBox.information(
                self, "Network audit",
                f"Found {len(findings)} loose endpoints. Review AUDIT layer."
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Network audit", str(exc))

    def unified_audit_csv(self):
        try:
            pipes = self.selected_vector_layer()
            parts = line_parts(pipes)
            segments = line_segments(pipes)
            nodes = []
            point_layers = [
                layer for layer in self.project.mapLayers().values()
                if isinstance(layer, QgsVectorLayer)
                and layer.isValid()
                and layer.geometryType() == QgsWkbTypes.PointGeometry
                and layer.crs() == pipes.crs()
            ]
            if point_layers:
                choices = ["None (pipes only)"] + [
                    f"{layer.name()} [{layer.id()}]" for layer in point_layers
                ]
                chosen, ok = QInputDialog.getItem(
                    self, "Unified audit", "Valve/riser layer:", choices, 0, False
                )
                if not ok:
                    return
                if chosen != choices[0]:
                    nodes = point_nodes(point_layers[choices.index(chosen) - 1], pipes.crs())
            findings = audit_network(parts, segments, nodes)
            path, _ = QFileDialog.getSaveFileName(
                self, 'Save unified audit report', '', 'CSV (*.csv)'
            )
            if not path:
                return
            if not path.lower().endswith('.csv'):
                path += '.csv'
            import csv
            with open(path, 'w', newline='', encoding='utf-8-sig') as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=['issue', 'asset', 'related', 'x', 'y']
                )
                writer.writeheader()
                writer.writerows(findings)
            QMessageBox.information(
                self, 'Unified audit',
                f'Exported {len(findings)} review findings. This is geometry QA only.'
            )
        except (ValueError, RuntimeError, OSError) as exc:
            QMessageBox.warning(self, 'Unified audit', str(exc))
    def audit_nodes(self):
        try:
            pipes = self.selected_vector_layer()
            segments = line_segments(pipes)
            endpoints = []
            for asset, start, end in line_parts(pipes):
                endpoints.extend([
                    (asset, 0, start[0], start[1]),
                    (asset, 1, end[0], end[1]),
                ])
            candidates = [
                layer for layer in self.project.mapLayers().values()
                if isinstance(layer, QgsVectorLayer)
                and layer.isValid()
                and layer.geometryType() == QgsWkbTypes.PointGeometry
                and layer.crs() == pipes.crs()
            ]
            if not candidates:
                raise ValueError("Load a valve or riser point layer with the same CRS")
            names = [f"{layer.name()} [{layer.id()}]" for layer in candidates]
            selected, ok = QInputDialog.getItem(
                self, "Select valve/riser layer", "Point layer:", names, 0, False
            )
            if not ok:
                return
            points = point_nodes(candidates[names.index(selected)], pipes.crs())
            matched, unmatched = match_nodes(endpoints, points)
            QMessageBox.information(
                self, "Valve/riser proximity",
                f"Endpoint checks: {len(endpoints)}; near points: {len(matched)}; "
                f"without nearby point: {len(unmatched)}. Tolerance: 0.05 m. "
                "This does not prove physical connectivity."
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Valve/riser proximity", str(exc))

    def audit_crossings(self):
        try:
            layer = self.selected_vector_layer()
            findings = crossing_candidates(line_segments(layer))
            if not findings:
                QMessageBox.information(self, "Crossing audit", "No interior crossings detected.")
                return
            markers = QgsVectorLayer(
                "Point?crs=" + layer.crs().authid(), "AUDIT - crossing candidates", "memory"
            )
            markers.dataProvider().addAttributes([
                QgsField("first", QVariant.String),
                QgsField("second", QVariant.String),
            ])
            markers.updateFields()
            features = []
            for item in findings:
                feature = QgsFeature(markers.fields())
                feature.setGeometry(QgsGeometry.fromPointXY(
                    QgsPointXY(item["x"], item["y"])
                ))
                feature.setAttributes([item["first"], item["second"]])
                features.append(feature)
            markers.dataProvider().addFeatures(features)
            markers.updateExtents()
            self.project.addMapLayer(markers)
            self.canvas.zoomToFullExtent()
            QMessageBox.information(
                self, "Crossing audit",
                f"{len(findings)} possible crossings added to the map. Review manually."
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Crossing audit", str(exc))

    def start_selected_edit(self):
        self.run_edit_action(start_editing)

    def save_selected_edit(self):
        self.run_edit_action(save_edits)

    def discard_selected_edit(self):
        layer = None
        try:
            layer = self.selected_vector_layer()
        except ValueError as exc:
            QMessageBox.warning(self, "Editing", str(exc))
            return
        answer = QMessageBox.question(
            self, "Discard edits", "Discard all unsaved edits on this layer?"
        )
        if answer == QMessageBox.Yes:
            self.run_edit_action(rollback_edits)

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open QGIS project", "", "QGIS projects (*.qgz *.qgs)"
        )
        if path and self.project.read(path):
            self.refresh_layers()
            self.canvas.zoomToFullExtent()
        elif path:
            QMessageBox.warning(self, "Open failed", "Could not load project.")

    def save_project(self):
        path = self.project.fileName()
        if not path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save QGIS project", "", "QGIS projects (*.qgz)"
            )
        if path:
            if not path.lower().endswith((".qgz", ".qgs")):
                path += ".qgz"
            self.project.setFileName(path)
            if not self.project.write():
                QMessageBox.warning(self, "Save failed", "Could not save project.")


def main():
    app = QgsApplication([], True)
    app.initQgis()
    window = MainWindow()
    window.show()
    result = app.exec_()
    window.close()
    app.exitQgis()
    return result


if __name__ == "__main__":
    sys.exit(main())
