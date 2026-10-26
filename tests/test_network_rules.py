import pytest
from gasgis.network_rules import NetworkRules, validate_service, find_duplicate_building_numbers


def test_valid_service():
    assert validate_service(4.0, 2.0, NetworkRules()) == []


def test_invalid_service():
    assert validate_service(6.0, 1.5, NetworkRules()) == [
        "SERVICE_TOO_LONG", "STREET_TOO_NARROW"
    ]


def test_boundary_values():
    assert validate_service(5.0, 1.8, NetworkRules()) == []


def test_negative_values_rejected():
    with pytest.raises(ValueError):
        validate_service(-1, 2, NetworkRules())


def test_duplicates():
    assert find_duplicate_building_numbers(["1", "2", "1", "", None, "2"]) == ["1", "2"]
