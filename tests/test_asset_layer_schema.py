"""Static contract tests; full GIS tests require QGIS runtime."""
import ast
from pathlib import Path


def test_gas_asset_layer_types_declared():
    path = Path(__file__).resolve().parents[1] / "gasgis" / "asset_layers.py"
    source = path.read_text(encoding="utf-8")
    for layer in ("gas_mains", "gas_services", "gas_valves", "gas_risers"):
        assert f'"{layer}"' in source
    ast.parse(source)


def test_gui_contains_gas_layer_action():
    path = Path(__file__).resolve().parents[1] / "gasgis" / "main.py"
    source = path.read_text(encoding="utf-8")
    assert "New gas layer" in source
    assert "validate_vector_path(path)" in source
    ast.parse(source)
