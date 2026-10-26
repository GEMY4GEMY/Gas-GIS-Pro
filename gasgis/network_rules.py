"""Pure-Python gas network geometry rules; engineering validation required."""
from dataclasses import dataclass


@dataclass(frozen=True)
class NetworkRules:
    main_diameter_mm: int = 63
    service_diameter_mm: int = 32
    max_service_length_m: float = 5.0
    min_street_width_m: float = 1.8
    building_inset_m: float = 1.0

    def __post_init__(self):
        if self.main_diameter_mm <= 0 or self.service_diameter_mm <= 0:
            raise ValueError("Diameters must be positive")
        if self.max_service_length_m <= 0 or self.min_street_width_m <= 0:
            raise ValueError("Distances must be positive")
        if self.building_inset_m < 0:
            raise ValueError("Inset cannot be negative")


def validate_service(length_m: float, street_width_m: float, rules: NetworkRules):
    """Return rule violations. Input distances must be in meters in a projected CRS."""
    if length_m < 0 or street_width_m < 0:
        raise ValueError("Distances cannot be negative")
    errors = []
    if length_m > rules.max_service_length_m:
        errors.append("SERVICE_TOO_LONG")
    if street_width_m < rules.min_street_width_m:
        errors.append("STREET_TOO_NARROW")
    return errors


def find_duplicate_building_numbers(numbers):
    """Return duplicate non-empty building identifiers in first-seen order."""
    seen = set()
    duplicates = []
    for value in numbers:
        key = str(value).strip() if value is not None else ""
        if not key:
            continue
        if key in seen and key not in duplicates:
            duplicates.append(key)
        seen.add(key)
    return duplicates
