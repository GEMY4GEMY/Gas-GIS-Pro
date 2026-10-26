# Connectivity analysis — prototype limitations

- `node_connectivity.match_nodes` checks whether pipe endpoints are within a metric tolerance of valve or riser points. It does not confirm fittings or actual hydraulic connection.
- `crossings.crossing_candidates` detects **interior intersections of straight 2D segments**. It intentionally excludes endpoint touches and collinear overlaps.
- For polylines, each consecutive vertex pair must be supplied as a segment; the current crossing function is not wired to the QGIS interface.
- Overpasses, pipe depth, diameter, valve state, fittings and flow direction are not modeled.
- These routines are quadratic in input size and require a spatial index for large projects.
- No physical design certification or operational safety determination is possible from these outputs.

## Next engineering milestones

1. Normalize all pipe polylines into segments and build a spatial index.
2. Validate CRS and metric units before comparing layers.
3. Differentiate geometric crossings from connected junctions.
4. Show node and crossing audit results in the desktop UI.
5. Run automated tests and Windows PyQGIS smoke tests.
