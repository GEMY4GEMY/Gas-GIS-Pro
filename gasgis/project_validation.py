"""Preflight validation for GIS input files."""
from pathlib import Path

SUPPORTED_VECTOR_EXTENSIONS = frozenset({".shp", ".gpkg", ".geojson", ".json", ".dxf"})


def validate_vector_path(path):
    """Return a list of validation issues before asking OGR to open the file."""
    file = Path(path)
    errors = []
    if not file.exists() or not file.is_file():
        return ["FILE_NOT_FOUND"]
    if file.suffix.lower() not in SUPPORTED_VECTOR_EXTENSIONS:
        errors.append("UNSUPPORTED_EXTENSION")
    if file.suffix.lower() == ".shp":
        for extension in (".shx", ".dbf"):
            companion = file.with_suffix(extension)
            if not companion.exists():
                errors.append(f"MISSING_{extension[1:].upper()}")
    return errors
