from core.expected_profile import ExpectedProfile


def test_expected_profile_builds_stable_key():
    profile = ExpectedProfile(
        brand="Tata", model="Nexon", manufacture_year=2022,
        variant="XZ+", fuel_type="Petrol", transmission="Manual",
        expected_annual_km_low=8_000, expected_annual_km_high=15_000,
        service_interval_months=12, known_issues=["Clutch wear"],
        maintenance_notes=["Annual service"], source="seed",
    )
    assert profile.profile_key == "tata|nexon|2022|xz+|petrol|manual"


def test_expected_profile_round_trip_record():
    profile = ExpectedProfile(
        brand="Honda", model="City", manufacture_year=2021,
        variant=None, fuel_type="Petrol", transmission="CVT",
        expected_annual_km_low=7_000, expected_annual_km_high=16_000,
        service_interval_months=12, known_issues=[],
        maintenance_notes=["Check CVT service history"], source="seed",
    )
    restored = ExpectedProfile.from_record(profile.to_record())
    assert restored == profile


def test_expected_profile_preserves_unknown_variant():
    profile = ExpectedProfile(
        brand="Tata", model="Nexon", manufacture_year=2022,
        variant=None, fuel_type=None, transmission=None,
        expected_annual_km_low=8_000, expected_annual_km_high=15_000,
        service_interval_months=12, known_issues=[], maintenance_notes=[],
        source="unknown",
    )
    assert profile.profile_key == "tata|nexon|2022|unknown|unknown|unknown"


def test_repository_saves_and_fetches_expected_profile(tmp_path):
    from core.database import Database
    db = Database(tmp_path / "test.db")
    profile = ExpectedProfile(
        brand="Maruti", model="Swift", manufacture_year=2020,
        variant="VXI", fuel_type="Petrol", transmission="Manual",
        expected_annual_km_low=8_000, expected_annual_km_high=15_000,
        service_interval_months=12, known_issues=["Clutch wear"],
        maintenance_notes=["Annual service"], source="seed",
    )
    db.save_expected_profile(profile)
    assert db.get_expected_profile(profile.profile_key) == profile


def test_repository_returns_none_for_missing_profile(tmp_path):
    from core.database import Database
    db = Database(tmp_path / "test.db")
    assert db.get_expected_profile("missing") is None
