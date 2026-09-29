from core.data_source import DataSource, ProviderResult
from core.expected_profile import ExpectedProfile
from core.models import Car
from core.profile_provider import SyntheticProfileProvider


def _profile():
    return ExpectedProfile(
        brand="Tata",
        model="Nexon",
        manufacture_year=2022,
        variant="XZ+",
        fuel_type="Petrol",
        transmission="Manual",
        expected_annual_km_low=8_000,
        expected_annual_km_high=15_000,
        service_interval_months=12,
        known_issues=["Clutch wear"],
        maintenance_notes=["Annual service"],
        source="synthetic_seed",
    )


def _car():
    return Car(
        car_id="CAR-1",
        brand="Tata",
        model="Nexon",
        manufacture_year=2022,
        variant="XZ+",
        fuel_type="Petrol",
        transmission="Manual",
    )


def test_provider_result_distinguishes_unavailable_from_not_found():
    source = DataSource("test", "Test source", "unknown")
    assert ProviderResult("UNAVAILABLE", source).available is False
    assert ProviderResult("NOT_FOUND", source).available is True
    assert ProviderResult("NOT_FOUND", source).found is False


def test_synthetic_provider_returns_profile_with_provenance():
    provider = SyntheticProfileProvider((_profile(),))
    result = provider.get_profile(_car())

    assert result.status == "FOUND"
    assert result.found is True
    assert result.data == _profile()
    assert result.source.source_id == "synthetic_seed"
    assert result.source.kind == "synthetic"


def test_synthetic_provider_reports_missing_profile_without_inventing_one():
    provider = SyntheticProfileProvider((_profile(),))
    car = Car(
        car_id="CAR-2",
        brand="UnknownBrand",
        model="UnknownModel",
        manufacture_year=2024,
    )

    result = provider.get_profile(car)

    assert result.status == "NOT_FOUND"
    assert result.data is None
    assert result.source.source_id == "synthetic_seed"
