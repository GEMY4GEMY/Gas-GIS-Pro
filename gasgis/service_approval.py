"""Read human approval CSV, validating against freshly calculated proposals.

No geometry is saved or edited by this module.
"""
import csv
from math import isclose


def approved_service_proposals(path, current_proposals, tolerance_m=0.001):
    """Accept only explicitly APPROVED, within-limit, geometry-matched rows.

    Fail closed on duplicates, unknown risers, changed coordinates or distances.
    """
    if tolerance_m < 0:
        raise ValueError("Tolerance cannot be negative")
    current = {}
    for proposal in current_proposals:
        key = str(proposal["riser_feature_id"])
        if key in current:
            raise ValueError("Multiple proposals for a single riser; approval ambiguous")
        current[key] = proposal
    approved = []
    seen = set()
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {
            "riser_id", "riser_x", "riser_y", "main_x", "main_y",
            "length_m", "distance_check", "engineering_approval"
        }
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Review CSV is missing required columns")
        for row in reader:
            key = row["riser_id"]
            if key in seen:
                raise ValueError(f"Duplicate riser in review CSV: {key}")
            seen.add(key)
            if key not in current:
                raise ValueError(f"Unknown riser in review CSV: {key}")
            proposal = current[key]
            try:
                coords = tuple(float(row[field]) for field in (
                    "riser_x", "riser_y", "main_x", "main_y"
                ))
                distance = float(row["length_m"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid coordinates or length for riser {key}") from exc
            expected = (*proposal["riser"], *proposal["main_point"])
            if not all(isclose(a, b, abs_tol=tolerance_m, rel_tol=0)
                       for a, b in zip(coords, expected)):
                raise ValueError(f"Network geometry changed for riser {key}")
            if not isclose(distance, proposal["distance_m"],
                           abs_tol=tolerance_m, rel_tol=0):
                raise ValueError(f"Connection length changed for riser {key}")
            status = "WITHIN_LIMIT" if proposal["within_limit"] else "OVER_LIMIT"
            if row["distance_check"] != status:
                raise ValueError(f"Distance status changed for riser {key}")
            approval = row["engineering_approval"].strip().upper()
            if approval not in {"APPROVED", "REJECTED", "PENDING"}:
                raise ValueError(f"Invalid approval status for riser {key}")
            if approval == "APPROVED":
                if not proposal["within_limit"]:
                    raise ValueError(f"Cannot approve over-limit riser {key}")
                approved.append(proposal)
    return approved
