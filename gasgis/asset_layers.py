"""Create a blank gas utility layer in a GeoPackage using PyQGIS.

Requires an initialized QgsApplication. Geometry is stored in a projected CRS
selected by the operator; the layer does not imply engineering approval.
"""
from pathlib import Path
import sqlite3

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsField,
    QgsVectorFileWriter, QgsWkbTypes, QgsProject, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant

SCHEMAS = {
    "gas_mains": (QgsWkbTypes.LineString, [
        ("asset_id", QVariant.String), ("diameter_mm", QVariant.Int),
        ("material", QVariant.String), ("pressure_class", QVariant.String),
        ("status", QVariant.String),
    ]),
    "gas_services": (QgsWkbTypes.LineString, [
        ("asset_id", QVariant.String), ("building_no", QVariant.String),
        ("diameter_mm", QVariant.Int), ("status", QVariant.String),
    ]),
    "gas_valves": (QgsWkbTypes.Point, [
        ("asset_id", QVariant.String), ("valve_type", QVariant.String),
        ("status", QVariant.String),
    ]),
    "gas_risers": (QgsWkbTypes.Point, [
        ("asset_id", QVariant.String), ("building_no", QVariant.String),
        ("status", QVariant.String),
    ]),
}


def create_asset_layer(gpkg_path, layer_name, crs_authid):
    """Create a new layer; reject invalid CRS, duplicates and existing files.

    Existing GeoPackages are deliberately not modified by this first version.
    """
    path = Path(gpkg_path)
    if path.suffix.lower() != ".gpkg":
        raise ValueError("Output must be a .gpkg file")
    if path.exists():
        raise FileExistsError("Choose a new GeoPackage path; overwrite is disabled")
    if layer_name not in SCHEMAS:
        raise ValueError("Unsupported asset layer type")
    crs = QgsCoordinateReferenceSystem(crs_authid)
    if not crs.isValid() or crs.isGeographic():
        raise ValueError("A valid projected CRS is required")
    if not path.parent.is_dir():
        raise FileNotFoundError("Output directory does not exist")
    return _write_asset_layer(path, layer_name, crs, append=False)


def append_asset_layer(gpkg_path, layer_name, crs_authid):
    """Append a new gas asset table without overwriting existing GeoPackage tables."""
    path = Path(gpkg_path)
    if path.suffix.lower() != '.gpkg' or not path.is_file():
        raise ValueError('Select an existing .gpkg file')
    if layer_name not in SCHEMAS:
        raise ValueError('Unsupported asset layer type')
    crs = QgsCoordinateReferenceSystem(crs_authid)
    if not crs.isValid() or crs.isGeographic():
        raise ValueError('A valid projected CRS is required')
    try:
        with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
            header = db.execute('PRAGMA application_id').fetchone()[0]
            if header != 0x47504B47:
                raise ValueError('File is not a GeoPackage')
            tables = {row[0].casefold() for row in db.execute('SELECT table_name FROM gpkg_contents')}
            if layer_name.casefold() in tables:
                raise FileExistsError(f'GeoPackage already contains {layer_name}')
            # Also reject an existing SQLite table not registered in gpkg_contents.
            existing = db.execute('SELECT 1 FROM sqlite_master WHERE lower(name)=lower(?)', (layer_name,)).fetchone()
            if existing:
                raise FileExistsError(f'GeoPackage already contains {layer_name}')
    except sqlite3.DatabaseError as exc:
        raise ValueError('File is not a readable GeoPackage') from exc
    return _write_asset_layer(path, layer_name, crs, append=True)


def _write_asset_layer(path, layer_name, crs, append):
    geometry, columns = SCHEMAS[layer_name]
    geom_name = "LineString" if geometry == QgsWkbTypes.LineString else "Point"
    layer = QgsVectorLayer(f"{geom_name}?crs={crs.authid()}", layer_name, "memory")
    if not layer.isValid():
        raise RuntimeError("Unable to create temporary GIS layer")
    layer.dataProvider().addAttributes([QgsField(name, typ) for name, typ in columns])
    layer.updateFields()
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = layer_name
    if append:
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
    result = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, str(path), QgsProject.instance().transformContext(), options
    )
    if result[0] != QgsVectorFileWriter.NoError:
        raise RuntimeError(f"GeoPackage export failed: {result[1]}")
    saved = QgsVectorLayer(f"{path}|layername={layer_name}", layer_name, "ogr")
    if not saved.isValid():
        raise RuntimeError("GeoPackage created but could not be reopened")
    return saved
