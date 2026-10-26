"""Safely enumerate GeoPackage feature tables without opening arbitrary SQL names."""
import sqlite3
from pathlib import Path


def geopackage_vector_tables(path):
    """Return registered feature layer names in a valid GeoPackage."""
    path = Path(path)
    if not path.is_file() or path.suffix.lower() != ".gpkg":
        raise ValueError("Select an existing GeoPackage (.gpkg)")
    try:
        with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
            application_id = db.execute("PRAGMA application_id").fetchone()[0]
            if application_id not in (0x47504B47, 0x47503130):
                raise ValueError("File is not a valid GeoPackage")
            names = [
                row[0] for row in db.execute(
                    "SELECT table_name FROM gpkg_contents "
                    "WHERE data_type IN ('features', 'attributes') ORDER BY table_name"
                )
            ]
    except sqlite3.DatabaseError as exc:
        raise ValueError("Cannot read GeoPackage metadata") from exc
    return names
