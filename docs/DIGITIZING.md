# Interactive drawing — development notes

1. Load or create a vector point or line layer in a **projected CRS**.
2. Select the layer in the Layers panel and click **Start editing**.
3. Click **Draw feature**. Left-click to add points or line vertices.
4. Right-click to finish a line. Point layers create one feature per click.
5. Click **Pan** to leave drawing mode, then **Save edits**.
6. Use **Undo** and **Redo** while editing. **Discard edits** rolls back all uncommitted changes.

## Known limitations
- Snapping currently targets vertices in all map layers, with a 12-pixel tolerance.
- Feature attributes are not prompted for during digitizing; populate them later.
- The attribute table is read-only.
- Geometry editing, vertex dragging, intersection splitting, and topology rules are not implemented.
- Runtime smoke testing on Windows with the packaged QGIS libraries is still pending.
- This is not yet a standalone Windows Portable EXE.
