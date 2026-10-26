# Editing and topology — prototype scope

## Editing
The UI exposes Start Editing, Save Edits, and Discard Edits for a selected vector layer.
Digitizing, snapping, undo/redo, and geometry edits are **not implemented** yet.
The attribute table remains read-only.

## Connectivity prototype
The pure-Python `endpoint_clusters` function groups coincident or near-coincident
segment endpoints in a projected CRS using a metric tolerance.
It does not detect interior intersections, overpasses, or valve connectivity.
The routine is O(n²), so large projects require a spatial index.
This function is not yet connected to the map UI.

Do not use these diagnostics for construction approval or operational gas safety decisions.
