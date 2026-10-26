# Map topology audit — development status

The toolbar now offers:

- **Audit pipe ends**: checks line endpoints and creates a temporary point layer for isolated ends; optional CSV.
- **Audit crossings**: creates a temporary point layer for interior crossings of straight segments.
- **Audit valve/riser proximity**: selects a same-CRS point layer and reports proximity counts.

## Limitations

- All input layers must use the same projected CRS in meters for cross-layer comparison.
- Crossing detection is 2D and does not distinguish a physical junction from an overpass.
- Endpoint-to-node proximity currently includes internal polyline vertices as endpoints of individual segments; it is a **proximity summary**, not a final connectivity assessment.
- Crossing checks are O(n²) and may be slow for large datasets.
- Valve/riser proximity has no detailed result layer yet.
- No Windows QGIS runtime smoke test or standalone Portable EXE has been completed.

The application must not be used to certify engineering safety.
