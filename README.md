# Gas GIS Pro

Professional desktop GIS for utility networks, specializing in natural gas distribution.

## Project status
Phase 1 — foundation. Source code and portable Windows releases are not yet built or validated.

## Technology direction
- QGIS / PyQGIS and Qt for desktop GIS
- GDAL/OGR for supported vector formats
- GeoPackage as local project data store
- Offline-first Windows portable distribution, installer after stabilization

## Phase 1 acceptance criteria
1. Start on a clean Windows 10/11 test system with bundled dependencies.
2. Load, inspect, style, and save vector layers.
3. Open and save QGIS project files without data loss.
4. Import DXF and Excel through documented workflows.
5. Run automated smoke tests and publish a downloadable portable build.

## Later modules
- Gas pipes, services, risers, valves and building links
- Topology checks and connectivity analysis
- Configurable engineering design rules, validated against applicable standards
- Quantity takeoff, reporting and print layouts
- Hydraulic calculations only after engineering validation

Safety: automated design outputs require professional review and compliance with applicable codes.
