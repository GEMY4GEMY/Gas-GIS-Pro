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
        self.layer_tree.blockSignals(True)
        self.layer_tree.clear()
        for layer in reversed(layers):
            item = QTreeWidgetItem([layer.name()])
            item.setData(0, Qt.UserRole, layer.id())
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Checked)
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
