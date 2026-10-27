"""Export proposed service connections for human review."""
import csv


def export_service_review_csv(path, proposals):
    """Write UTF-8 BOM CSV with both eligible and over-limit proposals."""
    with open(path, "w", encoding="utf-8-sig", newline="") as output:
        writer = csv.writer(output)
        writer.writerow([
            "riser_id", "riser_x", "riser_y", "main_x", "main_y",
            "length_m", "distance_check", "engineering_approval"
        ])
        for proposal in proposals:
            writer.writerow([
                proposal["riser_feature_id"],
                proposal["riser"][0], proposal["riser"][1],
                proposal["main_point"][0], proposal["main_point"][1],
                round(proposal["distance_m"], 3),
                "WITHIN_LIMIT" if proposal["within_limit"] else "OVER_LIMIT",
                "PENDING",
            ])
