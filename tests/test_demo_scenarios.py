from datetime import date

from core.assessment_pipeline import run_assessment
from core.database import Database
from core.demo_scenarios import build_demo_scenarios, get_demo_scenario


def test_demo_scenarios_have_stable_keys_and_complete_condition_data():
    scenarios = build_demo_scenarios()

    assert [scenario.key for scenario in scenarios] == ["clean", "negotiate", "critical"]
    for scenario in scenarios:
        assert scenario.car.car_id.startswith("DEMO-")
        assert scenario.condition.car_id == scenario.car.car_id
        assert all(value != "Unknown" for values in (
            scenario.condition.documents,
            scenario.condition.physical_inspection,
            scenario.condition.test_drive,
        ) for value in values.values())


def test_clean_demo_runs_through_pipeline(tmp_path):
    scenario = get_demo_scenario("clean")
    result = run_assessment(
        scenario.car,
        scenario.condition,
        Database(tmp_path / "clean.db"),
        today=date(2026, 9, 29),
    )

    assert result.assessment is not None
    assert result.assessment.verdict == "BUY"


def test_negotiation_demo_runs_through_pipeline(tmp_path):
    scenario = get_demo_scenario("negotiate")
    result = run_assessment(
        scenario.car,
        scenario.condition,
        Database(tmp_path / "negotiate.db"),
        today=date(2026, 9, 29),
    )

    assert result.assessment is not None
    assert result.assessment.verdict == "NEGOTIATE"
    assert len(result.assessment.warning_findings) >= 3


def test_critical_demo_runs_through_pipeline(tmp_path):
    scenario = get_demo_scenario("critical")
    result = run_assessment(
        scenario.car,
        scenario.condition,
        Database(tmp_path / "critical.db"),
        today=date(2026, 9, 29),
    )

    assert result.assessment is not None
    assert result.assessment.verdict == "AVOID"
    assert result.assessment.critical_findings


def test_unknown_demo_key_is_rejected():
    try:
        get_demo_scenario("missing")
    except ValueError as exc:
        assert "Unknown demo scenario" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
