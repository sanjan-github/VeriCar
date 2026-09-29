from datetime import date

from core.assessment import Assessment
from core.assessment_explanation import (
    build_explanation_evidence,
    generate_assessment_explanation,
)
from core.comparison import ComparisonFinding
from core.condition import ConditionRecord
from core.expected_profile import ExpectedProfile
from core.groq_llm import LLMExplanation
from core.models import Car
from core.rules import RuleFlag


class FakeLLM:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.evidence = None

    def explain(self, evidence):
        self.evidence = evidence
        if self.error:
            raise self.error
        return self.result


def make_inputs():
    car = Car(
        car_id="CAR-TEST123",
        brand="Tata",
        model="Nexon",
        manufacture_year=2022,
        variant="XZ+",
        fuel_type="Petrol",
        transmission="Manual",
        odometer_km=42000,
    )

    condition = ConditionRecord.empty(car.car_id)

    profile = ExpectedProfile(
        brand="Tata",
        model="Nexon",
        manufacture_year=2022,
        variant="XZ+",
        fuel_type="Petrol",
        transmission="Manual",
        expected_annual_km_low=8000,
        expected_annual_km_high=15000,
        service_interval_months=12,
        known_issues=["AC performance"],
        maintenance_notes=["Follow scheduled servicing"],
        source="synthetic_seed",
    )

    assessment = Assessment(
        verdict="NEGOTIATE",
        confidence=75,
        near_term_repair_range_inr=(10000, 12500),
        negotiation_reduction_inr=12500,
        next_checks=("Verify service invoices.",),
        critical_findings=(),
        warning_findings=("Mileage is above the expected range.",),
        info_findings=("Service history should be reviewed.",),
    )

    rule_flags = (
        RuleFlag(
            rule="odometer_vs_age",
            severity="warn",
            message="Mileage is above the expected range.",
            evidence=("expected_high=45000", "actual=52000"),
        ),
    )

    comparison_findings = (
        ComparisonFinding(
            category="service",
            severity="info",
            message="Service history should be reviewed.",
            evidence=("profile_interval_months=12",),
        ),
    )

    return car, condition, profile, assessment, rule_flags, comparison_findings


def test_build_explanation_evidence_preserves_deterministic_assessment():
    inputs = make_inputs()
    evidence = build_explanation_evidence(*inputs)

    assert evidence["deterministic_assessment"]["verdict"] == "NEGOTIATE"
    assert evidence["deterministic_assessment"]["confidence"] == 75
    assert evidence["deterministic_assessment"]["negotiation_reduction_inr"] == 12500
    assert evidence["rule_flags"][0]["rule"] == "odometer_vs_age"
    assert evidence["comparison_findings"][0]["category"] == "service"


def test_generate_assessment_explanation_returns_llm_result():
    inputs = make_inputs()
    result = LLMExplanation(
        summary="The evidence supports reviewing mileage and service history.",
        evidence_explanations=["Mileage is above the expected range."],
        contradictions=[],
        ai_estimates=[],
    )
    fake = FakeLLM(result=result)

    explanation = generate_assessment_explanation(*inputs, llm=fake)

    assert explanation is not None
    assert explanation.llm is result
    assert fake.evidence["deterministic_assessment"]["verdict"] == "NEGOTIATE"


def test_generate_assessment_explanation_does_not_break_on_groq_failure():
    inputs = make_inputs()
    fake = FakeLLM(error=RuntimeError("Groq unavailable"))

    explanation = generate_assessment_explanation(*inputs, llm=fake)

    assert explanation is None
