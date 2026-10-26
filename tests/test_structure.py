from pathlib import Path


def test_main_module_exists():
    assert (Path(__file__).resolve().parents[1] / 'gasgis' / 'main.py').is_file()
