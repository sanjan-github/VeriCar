from core.database import Database
from core.expected_profile import ExpectedProfile
from core.models import Car
from core.profile_resolver import profile_key_for_car, resolve_expected_profile


def make_car():
    return Car(
        car_id="CAR-1", brand="Tata", model="Nexon", manufacture_year=2022,
        variant="XZ+", fuel_type="Petrol", transmission="Manual",
    )


def make_profile():
    return ExpectedProfile(
        brand="Tata", model="Nexon", manufacture_year=2022,
        variant="XZ+", fuel_type="Petrol", transmission="Manual",
        expected_annual_km_low=8_000, expected_annual_km_high=15_000,
        service_interval_months=12, known_issues=["Clutch wear"],
        maintenance_notes=["Annual service"], source="seed",
    )


def test_profile_key_for_car_matches_expected_profile_key():
    car = make_car()
    assert profile_key_for_car(car) == make_profile().profile_key


def test_resolver_returns_missing_without_inventing_profile(tmp_path):
    db = Database(tmp_path / "test.db")
    result = resolve_expected_profile(make_car(), db)
    assert result.status == "MISSING"
    assert result.profile is None
    assert result.profile_key == "tata|nexon|2022|xz+|petrol|manual"


def test_resolver_returns_stored_profile(tmp_path):
    db = Database(tmp_path / "test.db")
    profile = make_profile()
    db.save_expected_profile(profile)

    result = resolve_expected_profile(make_car(), db)
    assert result.status == "FOUND"
    assert result.profile == profile


def test_resolver_handles_missing_optional_configuration_fields(tmp_path):
    db = Database(tmp_path / "test.db")
    car = Car("CAR-2", "Honda", "City", 2021)
    result = resolve_expected_profile(car, db)
    assert result.status == "MISSING"
    assert result.profile_key == "honda|city|2021|unknown|unknown|unknown"
