from backend.app.services.evidence_service import EvidenceService
from backend.tests.vehicle_history_scenarios import SCENARIOS


def test_single_supporting_report_remains_limited_evidence():
    scenario = SCENARIOS["single_supporting"]
    report = scenario.reports[0]

    assert report.claim.report_id == report.report_id
    assert report.claim.polarity == "supporting"

    result = EvidenceService().classify("transmission_shift_behavior", scenario.evidence())

    assert len(scenario.reports) == 1
    assert result.independent_supporting_sources == 1
    assert result.supporting_evidence[0].text == report.text
    assert result.state == "limited_evidence"


def test_independent_sources_add_supporting_evidence():
    scenario = SCENARIOS["independent_support"]
    result = EvidenceService().classify("transmission_shift_behavior", scenario.evidence())

    assert result.independent_supporting_sources == 2
    assert {item.source_id for item in result.supporting_evidence} == {
        report.source_id for report in scenario.reports
    }


def test_contradicting_claim_and_supporting_claim_are_both_preserved():
    scenario = SCENARIOS["contradiction"]
    result = EvidenceService().classify("transmission_shift_behavior", scenario.evidence())

    assert [item.evidence_id for item in result.contradicting_evidence] == ["RPT-103-A"]
    assert [item.evidence_id for item in result.supporting_evidence] == ["RPT-103-B"]
    assert result.contradiction_weight > 0


def test_same_source_reports_remain_distinct_but_count_as_one_source():
    scenario = SCENARIOS["same_source_repetition"]
    evidence = scenario.evidence()
    result = EvidenceService().classify("transmission_shift_behavior", evidence)

    assert len(evidence) == 2
    assert {item.evidence_id for item in evidence} == {"RPT-104-A", "RPT-104-B"}
    assert result.independent_supporting_sources == 1
    assert len(result.supporting_evidence) == 1


def test_unresolved_evidence_does_not_create_support_or_contradiction():
    scenario = SCENARIOS["unresolved"]
    result = EvidenceService().classify("transmission_shift_behavior", scenario.evidence())

    assert len(result.unresolved_evidence) == 1
    assert result.supporting_evidence == ()
    assert result.contradicting_evidence == ()
    assert result.confidence is None


def test_source_types_and_observation_dates_are_preserved():
    scenario = SCENARIOS["temporal_progression"]
    result = EvidenceService().classify("transmission_shift_behavior", scenario.evidence())

    assert [item.observed_at for item in result.contradicting_evidence + result.supporting_evidence] == [
        report.observed_at for report in scenario.reports
    ]
    assert {report.source_type for report in scenario.reports} == {"owner", "buyer", "mechanic"}
    assert result.contradicting_evidence[0].source_type == "owner"
    assert {item.source_type for item in result.supporting_evidence} == {"buyer", "mechanic"}


def test_empty_history_is_insufficient_evidence():
    scenario = SCENARIOS["insufficient_history"]
    result = EvidenceService().classify("transmission_shift_behavior", scenario.evidence())

    assert scenario.reports == ()
    assert result.state == "insufficient_evidence"
    assert result.confidence is None
