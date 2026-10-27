import csv

from gasgis.service_review_export import export_service_review_csv


def test_service_review_csv(tmp_path):
    path = tmp_path / "review.csv"
    proposals = [
        {"riser_feature_id": 1, "riser": (0, 4), "main_point": (0, 0),
         "distance_m": 4.0, "within_limit": True},
        {"riser_feature_id": 2, "riser": (0, 7), "main_point": (0, 0),
         "distance_m": 7.0, "within_limit": False},
    ]
    export_service_review_csv(path, proposals)
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 2
    assert [row["distance_check"] for row in rows] == ["WITHIN_LIMIT", "OVER_LIMIT"]
    assert all(row["engineering_approval"] == "PENDING" for row in rows)
    assert rows[1]["length_m"] == "7.0"
