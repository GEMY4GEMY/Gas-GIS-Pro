# Unified audit CSV

Choose a projected meter-based pipe line layer, then click **Unified audit CSV**.
The exported UTF-8 BOM CSV includes `issue`, `asset`, `related`, `x`, `y`.

The toolbar export currently includes **LOOSE_END** and **CROSSING** only.
The underlying `audit_network` function also supports **NO_NEARBY_NODE** when explicit valve/riser point coordinates are supplied, but the toolbar export does not yet request a point layer.

This report is an engineering geometry review aid only. Crossings are not necessarily connected junctions, and isolated ends can be intentional. The implementation has not yet been validated in a Windows QGIS runtime or packaged as a Portable EXE.

If a valve/riser point layer is explicitly selected but contains zero points, the audit reports every pipe-part endpoint as `NO_NEARBY_NODE`. Skipping the point layer does not generate these findings.
