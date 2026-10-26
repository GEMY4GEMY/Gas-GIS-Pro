from gasgis.audit_export import export_audit_csv
import csv


def test_export_csv(tmp_path):
    path = tmp_path / "audit.csv"
    count = export_audit_csv(
        [{"asset": "pipe-1", "end": 0, "x": 1.5, "y": 2.5}], path
    )
    assert count == 1
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["asset"] == "pipe-1"
    assert rows[0]["x"] == "1.5"
