"""Tests for read-only GeoPackage spatial layer discovery."""
import sqlite3

import pytest

from gasgis.geopackage_catalog import geopackage_vector_tables


def test_rejects_missing_file(tmp_path):
    with pytest.raises(ValueError, match="existing GeoPackage"):
        geopackage_vector_tables(tmp_path / "missing.gpkg")


def test_rejects_ordinary_sqlite(tmp_path):
    path = tmp_path / "ordinary.gpkg"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE dummy (id INTEGER)")
    with pytest.raises(ValueError, match="not a valid GeoPackage"):
        geopackage_vector_tables(path)


def test_returns_only_spatial_layers_sorted(tmp_path):
    path = tmp_path / "assets.gpkg"
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA application_id = 1196444487")
        db.execute("CREATE TABLE gpkg_contents (table_name TEXT, data_type TEXT)")
        db.executemany(
            "INSERT INTO gpkg_contents VALUES (?, ?)",
            [
                ("gas_risers", "features"),
                ("prices", "attributes"),
                ("gas_mains", "features"),
                ("background", "tiles"),
            ],
        )
    assert geopackage_vector_tables(path) == ["gas_mains", "gas_risers"]


def test_reports_missing_contents_table(tmp_path):
    path = tmp_path / "broken.gpkg"
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA application_id = 1196444487")
    with pytest.raises(ValueError, match="Cannot read GeoPackage metadata"):
        geopackage_vector_tables(path)
