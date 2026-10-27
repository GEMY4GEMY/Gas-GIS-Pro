import csv

import pytest

from gasgis.service_approval import approved_service_proposals
from gasgis.service_review_export import export_service_review_csv


@pytest.fixture
def review(tmp_path):
    proposals = [
        {"riser_feature_id": 1, "riser": (1, 4), "main_point": (1, 0),
         "distance_m": 4.0, "within_limit": True},
        {"riser_feature_id": 2, "riser": (2, 7), "main_point": (2, 0),
         "distance_m": 7.0, "within_limit": False},
    ]
    path = tmp_path / "review.csv"
    export_service_review_csv(path, proposals)
    return path, proposals


def edit_review(path, changes):
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    for index, fields in changes.items():
        rows[index].update(fields)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def test_pending_not_approved(review):
    path, proposals = review
    assert approved_service_proposals(path, proposals) == []


def test_explicit_approval_only(review):
    path, proposals = review
    edit_review(path, {0: {"engineering_approval": "APPROVED"},
                       1: {"engineering_approval": "REJECTED"}})
    assert approved_service_proposals(path, proposals) == [proposals[0]]


def test_over_limit_approval_rejected(review):
    path, proposals = review
    edit_review(path, {1: {"engineering_approval": "APPROVED"}})
    with pytest.raises(ValueError, match="over-limit"):
        approved_service_proposals(path, proposals)


def test_changed_geometry_rejected(review):
    path, proposals = review
    edit_review(path, {0: {"main_x": "100"}})
    with pytest.raises(ValueError, match="geometry changed"):
        approved_service_proposals(path, proposals)


def test_duplicate_riser_rejected(review):
    path, proposals = review
    edit_review(path, {1: {"riser_id": "1"}})
    with pytest.raises(ValueError, match="Duplicate"):
        approved_service_proposals(path, proposals)
