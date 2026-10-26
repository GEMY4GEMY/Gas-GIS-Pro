# Windows portable build plan

**Current status:** Not yet a standalone portable application.

## Runtime bundling milestones
1. Pin QGIS LTR and Python/Qt/GDAL compatible versions.
2. Bundle a legally redistributable QGIS runtime and required plugins.
3. Configure QGIS_PREFIX_PATH, QT_PLUGIN_PATH, GDAL_DATA and PROJ_DATA using relative paths.
4. Create a launcher and test from a path containing spaces and Arabic characters.
5. Test on clean Windows 10 and Windows 11 VMs without QGIS installed.
6. Publish a ZIP artifact with checksum, licenses, smoke-test evidence and known limitations.

Do not label a source ZIP as an executable build.
