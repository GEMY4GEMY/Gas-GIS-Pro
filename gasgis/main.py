"""Gas GIS Pro — Phase 1 desktop GIS shell (requires QGIS Python environment)."""
import sys
from pathlib import Path

from qgis.core import QgsApplication, QgsProject, QgsVectorLayer
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QToolBar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gas GIS Pro — Development")
        self.resize(1280, 800)
        self.project = QgsProject.instance()
        self.canvas = QgsMapCanvas()
        self.canvas.setCanvasColor(Qt.white)
        self.setCentralWidget(self.canvas)
        toolbar = QToolBar("Project")
        self.addToolBar(toolbar)
        for title, callback in (
            ("Open layer", self.open_layer),
            ("Open project", self.open_project),
            ("Save project", self.save_project),
            ("Zoom full", self.canvas.zoomToFullExtent),
        ):
            toolbar.addAction(title, callback)
        self.statusBar().showMessage("Development build — not validated for production")

    def refresh_layers(self):
        layers = [layer for layer in self.project.mapLayers().values() if layer.isValid()]
        self.canvas.setLayers(layers)
        if layers:
            self.canvas.zoomToFullExtent()
        self.canvas.refresh()

    def open_layer(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open vector layer", "",
            "Vector files (*.shp *.gpkg *.geojson *.json *.dxf);;All files (*)"
        )
        if not path:
            return
        layer = QgsVectorLayer(path, Path(path).stem, "ogr")
        if not layer.isValid():
            QMessageBox.warning(self, "Import failed", "Unable to load the layer.")
            return
        self.project.addMapLayer(layer)
        self.refresh_layers()

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open QGIS project", "", "QGIS projects (*.qgz *.qgs)"
        )
        if path and self.project.read(path):
            self.refresh_layers()
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
