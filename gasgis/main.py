"""Gas GIS Pro desktop GIS shell. Requires a working PyQGIS runtime."""
import sys
from pathlib import Path

from qgis.core import QgsApplication, QgsProject, QgsVectorLayer
from qgis.gui import QgsMapCanvas, QgsMapToolPan
from qgis.PyQt.QtCore import Qt
from gasgis.project_validation import validate_vector_path
from gasgis.geopackage_catalog import geopackage_vector_tables
from gasgis.asset_layers import create_asset_layer, append_asset_layer, SCHEMAS
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
from qgis.core import QgsSnappingConfig, QgsWkbTypes, QgsLineSymbol, QgsMarkerSymbol
from qgis.PyQt.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QToolBar, QDockWidget,
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QInputDialog, QColorDialog
)


GAS_STYLES = {
    "gas_mains": ("line", {"line_color": "#c0392b", "line_width": "0.9"}),
    "gas_services": ("line", {"line_color": "#e67e22", "line_width": "0.5"}),
    "gas_valves": ("point", {"color": "#2980b9", "size": "3.5"}),
    "gas_risers": ("point", {"color": "#27ae60", "size": "2.8"}),
}


def apply_gas_style(layer):
    """Apply the standard symbol for a matching gas asset vector layer."""
    style = GAS_STYLES.get(layer.name())
    if style is None:
        return False
    kind, properties = style
    expected = QgsWkbTypes.LineGeometry if kind == "line" else QgsWkbTypes.PointGeometry
    if layer.geometryType() != expected:
        return False
    renderer = layer.renderer()
    if renderer is None or not hasattr(renderer, "setSymbol"):
        return False
    symbol = (
        QgsLineSymbol.createSimple(properties)
        if kind == "line" else QgsMarkerSymbol.createSimple(properties)
    )
    renderer.setSymbol(symbol)
    layer.triggerRepaint()
    return True


def _matches_numeric(candidate, expected):
    try:
        return float(candidate) == expected
    except (TypeError, ValueError):
        return False


def _compare_attribute(candidate, expected, operator, numeric):
    """Compare non-null attributes using an explicitly allowed operator."""
    if candidate is None or str(candidate) == "NULL":
        return False
    if numeric:
        try:
            candidate = float(candidate)
        except (TypeError, ValueError):
            return False
    else:
        candidate = str(candidate)
    return {
        "=": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
    }[operator](candidate, expected)


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
            ("Zoom to layer", self.zoom_to_selected_layer),
            ("Remove layer", self.remove_selected_layer),
            ("Rename layer", self.rename_selected_layer),
            ("Layer color", self.set_selected_layer_color),
            ("Symbol size", self.set_selected_symbol_size),
            ("Gas style", self.apply_gas_layer_style),
            ("Style all gas layers", self.style_all_gas_layers),
            ("Select by attribute", self.select_by_attribute),
            ("Select by location", self.select_by_location),
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
        self.refresh_layers()
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
            node = self.project.layerTreeRoot().findLayer(layer.id())
            visible = self.layer_visibility.get(
                layer.id(), node.itemVisibilityChecked() if node else True
            )
            item.setCheckState(0, Qt.Checked if visible else Qt.Unchecked)
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
        layer_id = item.data(0, Qt.UserRole)
        visible = item.checkState(0) == Qt.Checked
        self.layer_visibility[layer_id] = visible
        node = self.project.layerTreeRoot().findLayer(layer_id)
        if node is not None:
            node.setItemVisibilityChecked(visible)
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
        if Path(path).suffix.lower() == ".gpkg":
            try:
                names = geopackage_vector_tables(path)
            except ValueError as exc:
                QMessageBox.warning(self, "GeoPackage error", str(exc))
                return
            if not names:
                QMessageBox.warning(self, "GeoPackage error", "No spatial feature layers found.")
                return
            if len(names) > 1:
                choices = ["All layers"] + names
                choice, ok = QInputDialog.getItem(
                    self, "Open GeoPackage", "Choose layer(s):", choices, 0, False
                )
                if not ok:
                    return
                names = names if choice == "All layers" else [choice]
            existing_sources = {
                layer.source() for layer in self.project.mapLayers().values()
                if isinstance(layer, QgsVectorLayer)
            }
            candidates = [
                (name, f"{path}|layername={name}") for name in names
            ]
            candidates = [
                (name, source) for name, source in candidates
                if source not in existing_sources
            ]
            if not candidates:
                self.statusBar().showMessage("Selected GeoPackage layers are already open.", 5000)
                return
            layers = [
                QgsVectorLayer(source, name, "ogr") for name, source in candidates
            ]
            invalid = [
                name for (name, _), layer in zip(candidates, layers) if not layer.isValid()
            ]
            if invalid:
                QMessageBox.warning(self, "Import failed", "Unable to load: " + ", ".join(invalid))
                return
            for layer in layers:
                self.project.addMapLayer(layer)
        else:
            layer = QgsVectorLayer(path, Path(path).stem, "ogr")
            if not layer.isValid():
                QMessageBox.warning(self, "Import failed", "Unable to load the layer.")
                return
            self.project.addMapLayer(layer)
        self.canvas.zoomToFullExtent()

    def zoom_to_selected_layer(self):
        """Zoom the map to the selected layer without changing visibility."""
        item = self.layer_tree.currentItem()
        layer = self.project.mapLayer(item.data(0, Qt.UserRole)) if item else None
        if layer is None or not layer.isValid():
            self.statusBar().showMessage("Select a layer first.", 5000)
            return
        extent = layer.extent()
        if extent.isNull() or extent.isEmpty():
            self.statusBar().showMessage("Selected layer has no spatial extent.", 5000)
            return
        self.canvas.setExtent(extent)
        self.canvas.refresh()

    def select_by_location(self):
        """Select features intersecting another layer in the same CRS."""
        try:
            target = self.selected_vector_layer()
        except ValueError as exc:
            QMessageBox.warning(self, "Select by location", str(exc))
            return
        candidates = [
            layer for layer in self.project.mapLayers().values()
            if isinstance(layer, QgsVectorLayer) and layer.isValid()
            and layer.id() != target.id() and layer.crs() == target.crs()
        ]
        if not candidates:
            QMessageBox.information(
                self, "Select by location",
                "Add another vector layer with the same CRS to select against."
            )
            return
        labels = [f"{layer.name()} [{layer.id()}]" for layer in candidates]
        choice, ok = QInputDialog.getItem(
            self, "Select by location", "Intersects layer:", labels, 0, False
        )
        if not ok:
            return
        source = candidates[labels.index(choice)]
        geometries = [
            feature.geometry() for feature in source.getFeatures()
            if feature.hasGeometry() and not feature.geometry().isEmpty()
        ]
        selected = []
        for feature in target.getFeatures():
            if not feature.hasGeometry() or feature.geometry().isEmpty():
                continue
            geometry = feature.geometry()
            if any(geometry.intersects(other) for other in geometries):
                selected.append(feature.id())
        target.selectByIds(selected)
        self.statusBar().showMessage(
            f"Selected {len(selected)} intersecting feature(s).", 8000
        )

    def select_by_attribute(self):
        """Select features matching an exact field value without SQL expression injection."""
        try:
            layer = self.selected_vector_layer()
        except ValueError as exc:
            QMessageBox.warning(self, "Select by attribute", str(exc))
            return
        fields = [field.name() for field in layer.fields()]
        if not fields:
            QMessageBox.information(self, "Select by attribute", "Layer has no fields.")
            return
        field_name, ok = QInputDialog.getItem(
            self, "Select by attribute", "Field:", fields, 0, False
        )
        if not ok:
            return
        operator, ok = QInputDialog.getItem(
            self, "Select by attribute", "Operator:",
            ["=", "!=", ">", ">=", "<", "<="], 0, False
        )
        if not ok:
            return
        value, ok = QInputDialog.getText(
            self, "Select by attribute", f"Value for {field_name}:"
        )
        if not ok:
            return
        index = layer.fields().indexFromName(field_name)
        field = layer.fields().at(index)
        if not field.isNumeric() and operator not in ("=", "!="):
            QMessageBox.warning(
                self, "Select by attribute", "Ordering operators require a numeric field."
            )
            return
        if field.isNumeric():
            try:
                typed_value = float(value)
            except ValueError:
                QMessageBox.warning(
                    self, "Select by attribute", "Enter a valid numeric value."
                )
                return
        else:
            typed_value = value
        matches = [
            feature.id() for feature in layer.getFeatures()
            if _compare_attribute(
                feature.attributes()[index], typed_value, operator, field.isNumeric()
            )
        ]
        layer.selectByIds(matches)
        self.statusBar().showMessage(f"Selected {len(matches)} feature(s).", 8000)


    def style_all_gas_layers(self):
        """Apply standard symbols to all recognized gas asset layers in this project."""
        count = 0
        for layer in self.project.mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and layer.isValid():
                if apply_gas_style(layer):
                    count += 1
        self.canvas.refresh()
        self.statusBar().showMessage(
            f"Styled {count} gas asset layer(s); save project to keep changes.", 8000
        )

    def apply_gas_layer_style(self):
        """Apply standard visual styles for known gas asset layers."""
        item = self.layer_tree.currentItem()
        layer = self.project.mapLayer(item.data(0, Qt.UserRole)) if item else None
        if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            self.statusBar().showMessage("Select a gas asset layer first.", 5000)
            return
        style = GAS_STYLES.get(layer.name())
        if style is None:
            QMessageBox.information(
                self, "Gas style", "Rename the layer to a standard gas asset name first."
            )
            return
        kind, properties = style
        expected = (
            QgsWkbTypes.LineGeometry if kind == "line" else QgsWkbTypes.PointGeometry
        )
        if layer.geometryType() != expected:
            QMessageBox.warning(
                self, "Gas style", "Layer geometry does not match the gas asset type."
            )
            return
        symbol = (
            QgsLineSymbol.createSimple(properties)
            if kind == "line" else QgsMarkerSymbol.createSimple(properties)
        )
        renderer = layer.renderer()
        if renderer is None or not hasattr(renderer, "setSymbol"):
            QMessageBox.warning(self, "Gas style", "Layer renderer is not a single-symbol renderer.")
            return
        renderer.setSymbol(symbol)
        layer.triggerRepaint()
        self.canvas.refresh()
        self.statusBar().showMessage("Gas style applied; save project to preserve it.", 5000)

    def set_selected_symbol_size(self):
        """Set point marker size or line width in millimeters (project style)."""
        item = self.layer_tree.currentItem()
        layer = self.project.mapLayer(item.data(0, Qt.UserRole)) if item else None
        if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            self.statusBar().showMessage("Select a vector layer first.", 5000)
            return
        geometry_type = layer.geometryType()
        if geometry_type not in (QgsWkbTypes.PointGeometry, QgsWkbTypes.LineGeometry):
            QMessageBox.information(
                self, "Symbol size", "Only point and line layers are supported."
            )
            return
        renderer = layer.renderer()
        symbol = renderer.symbol() if renderer is not None else None
        if symbol is None:
            QMessageBox.warning(self, "Symbol size", "This layer has no editable single symbol.")
            return
        is_line = geometry_type == QgsWkbTypes.LineGeometry
        current = symbol.width() if is_line else symbol.size()
        size, ok = QInputDialog.getDouble(
            self, "Symbol size",
            "Line width (mm):" if is_line else "Marker size (mm):",
            current, 0.1, 20.0, 2
        )
        if not ok:
            return
        if is_line:
            symbol.setWidth(size)
        else:
            symbol.setSize(size)
        layer.triggerRepaint()
        self.canvas.refresh()
        self.statusBar().showMessage("Symbol size updated; save project to keep it.", 5000)

    def set_selected_layer_color(self):
        """Change the map symbol color of a vector layer (project styling only)."""
        item = self.layer_tree.currentItem()
        layer = self.project.mapLayer(item.data(0, Qt.UserRole)) if item else None
        if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            self.statusBar().showMessage("Select a vector layer first.", 5000)
            return
        geometry_type = layer.geometryType()
        if geometry_type not in (QgsWkbTypes.PointGeometry, QgsWkbTypes.LineGeometry):
            QMessageBox.information(
                self, "Layer color", "Currently supported for point and line layers."
            )
            return
        color = QColorDialog.getColor(parent=self, title="Choose layer color")
        if not color.isValid():
            return
        symbol = (
            QgsLineSymbol.createSimple({"line_color": color.name()})
            if geometry_type == QgsWkbTypes.LineGeometry
            else QgsMarkerSymbol.createSimple({"color": color.name()})
        )
        layer.renderer().setSymbol(symbol)
        layer.triggerRepaint()
        self.canvas.refresh()
        self.statusBar().showMessage("Layer color updated; save project to keep it.", 5000)

    def rename_selected_layer(self):
        """Rename the selected map layer display name, without renaming its data source."""
        item = self.layer_tree.currentItem()
        layer = self.project.mapLayer(item.data(0, Qt.UserRole)) if item else None
        if layer is None:
            self.statusBar().showMessage("Select a layer first.", 5000)
            return
        name, ok = QInputDialog.getText(
            self, "Rename layer", "Display name:", text=layer.name()
        )
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.warning(self, "Invalid layer name", "Layer name cannot be empty.")
            return
        if name == layer.name():
            return
        layer.setName(name)
        self.refresh_layers()
        self.statusBar().showMessage("Layer display name updated; source file unchanged.", 5000)

    def remove_selected_layer(self):
        """Remove a map layer from the project, never its source dataset."""
        item = self.layer_tree.currentItem()
        layer = self.project.mapLayer(item.data(0, Qt.UserRole)) if item else None
        if layer is None:
            self.statusBar().showMessage("Select a layer first.", 5000)
            return
        if isinstance(layer, QgsVectorLayer) and layer.isEditable():
            QMessageBox.warning(
                self, "Unsaved edits",
                "Save or discard edits before removing this layer."
            )
            return
        answer = QMessageBox.question(
            self, "Remove layer",
            f"Remove '{layer.name()}' from the current project?\n"
            "The source file will not be deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.project.removeMapLayer(layer.id())
        self.statusBar().showMessage("Layer removed from project; source file preserved.", 5000)

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
        mode, ok = QInputDialog.getItem(
            self, "GeoPackage destination", "Destination:",
            ["Create new GeoPackage", "Add to existing GeoPackage"], 0, False
        )
        if not ok:
            return
        append = mode == "Add to existing GeoPackage"
        if append:
            path, _ = QFileDialog.getOpenFileName(
                self, "Select existing GeoPackage", "", "GeoPackage (*.gpkg)"
            )
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "New gas GeoPackage", "", "GeoPackage (*.gpkg)"
            )
        if not path:
            return
        if not append and not path.lower().endswith(".gpkg"):
            path += ".gpkg"
        try:
            if append:
                layer = append_asset_layer(path, layer_name, crs.strip())
            else:
                layer = create_asset_layer(path, layer_name, crs.strip())
        except (ValueError, FileExistsError, FileNotFoundError, RuntimeError) as exc:
            QMessageBox.warning(self, "Create layer failed", str(exc))
            return
        apply_gas_style(layer)
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
        except (ValueError, RuntimeError, OSError) as exc:
            QMessageBox.warning(self, "Network audit", str(exc))

    def unified_audit_csv(self):
        try:
            pipes = self.selected_vector_layer()
            parts = line_parts(pipes)
            segments = line_segments(pipes)
            nodes = None
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

    def active_edit_layers(self):
        return [
            layer.name() for layer in self.project.mapLayers().values()
            if isinstance(layer, QgsVectorLayer) and layer.isEditable()
        ]

    def confirm_close(self):
        active = self.active_edit_layers()
        if not active:
            return True
        QMessageBox.warning(
            self, "Unsaved edits",
            "Save or discard active layer edits before closing: "
            + ", ".join(active)
        )
        return False

    def closeEvent(self, event):
        if self.confirm_close():
            event.accept()
        else:
            event.ignore()

    def open_project(self):
        editable = self.active_edit_layers()
        if editable:
            QMessageBox.warning(
                self, "Unsaved edits",
                "Save or discard active layer edits before opening another project: "
                + ", ".join(editable)
            )
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open QGIS project", "", "QGIS projects (*.qgz *.qgs)"
        )
        if path and self.project.read(path):
            self.layer_visibility.clear()
            self.refresh_layers()
            self.canvas.zoomToFullExtent()
        elif path:
            QMessageBox.warning(self, "Open failed", "Could not load project.")

    def save_project(self):
        editable = self.active_edit_layers()
        if editable:
            QMessageBox.warning(
                self, "Unsaved edits",
                "Save or discard active layer edits before saving the project: "
                + ", ".join(editable)
            )
            return
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
    # Qt invokes closeEvent when the user closes the window.
    # Do not force another close here: unsaved edits may have blocked it.
    del window
    return result


if __name__ == "__main__":
    sys.exit(main())
