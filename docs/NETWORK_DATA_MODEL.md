# Gas network data model — first iteration

The desktop application can create **one new layer per new GeoPackage file**.
It does not yet append multiple asset layers to the same GeoPackage.

| Layer | Geometry | Fields |
|---|---|---|
| gas_mains | LineString | asset_id, diameter_mm, material, pressure_class, status |
| gas_services | LineString | asset_id, building_no, diameter_mm, status |
| gas_valves | Point | asset_id, valve_type, status |
| gas_risers | Point | asset_id, building_no, status |

All layers require an operator-selected projected CRS. EPSG:32636 is an example only, not a universal Egypt CRS.

## Not yet implemented
- Feature digitizing/editing and undo/redo
- Multi-layer GeoPackage append
- Referential integrity and topology constraints
- Gas flow or pressure simulation
- Engineering approvals or compliance checks

**Safety:** These are data structures only. They do not certify pipeline design.
