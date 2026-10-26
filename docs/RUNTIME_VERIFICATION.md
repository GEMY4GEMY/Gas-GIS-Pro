# QGIS runtime verification checklist

The `QGIS runtime smoke test` workflow runs on Ubuntu 24.04 with distro PyQGIS and a virtual display. It checks:

1. Importing the desktop application.
2. Creating a main window.
3. Creating and reading a temporary projected line layer.
4. Distinguishing whole line-part endpoints from individual vertex segments.
5. Running the geometry audit.
6. Synchronizing layer visibility with the QGIS layer tree.
7. Creating and reopening a GeoPackage asset layer.

## Important release gates

- A successful workflow run must be confirmed in GitHub Actions; committing a workflow is not evidence it passed.
- Windows runtime testing is separate from Ubuntu PyQGIS testing.
- Windows Portable needs a pinned, redistribution-compatible QGIS/Qt/GDAL/Python bundle and a clean-machine launch test.
- Do not publish a release labelled Portable until launch, edit, save, reopen and export pass on Windows without separately installed QGIS.
- Audit findings are advisory geometry checks, not hydraulic design approval.
