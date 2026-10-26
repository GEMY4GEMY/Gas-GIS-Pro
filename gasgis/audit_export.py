"""Export network audit findings to CSV without changing project data."""
import csv
from pathlib import Path


def export_audit_csv(findings, destination):
    path = Path(destination)
    if path.suffix.lower() != ".csv":
        raise ValueError("Audit export must be CSV")
    if not path.parent.is_dir():
        raise FileNotFoundError("Output directory not found")
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["asset", "end", "x", "y"])
        writer.writeheader()
        for item in findings:
            writer.writerow({name: item[name] for name in writer.fieldnames})
    return len(findings)
