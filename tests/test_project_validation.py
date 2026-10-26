from gasgis.project_validation import validate_vector_path


def test_missing_file(tmp_path):
    assert validate_vector_path(tmp_path / "missing.shp") == ["FILE_NOT_FOUND"]


def test_geojson(tmp_path):
    path = tmp_path / "a.geojson"
    path.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
    assert validate_vector_path(path) == []


def test_shapefile_sidecars(tmp_path):
    path = tmp_path / "a.shp"
    path.write_bytes(b"")
    assert validate_vector_path(path) == ["MISSING_SHX", "MISSING_DBF"]
    path.with_suffix(".shx").write_bytes(b"")
    path.with_suffix(".dbf").write_bytes(b"")
    assert validate_vector_path(path) == []
