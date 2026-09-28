from datetime import date

import pytest

from backend.app.models.evidence import EvidenceRecord, SourceHistory
from backend.app.services.evidence_service import EvidenceService


@pytest.fixture
def service():
    return EvidenceService()


def evidence(
    evidence_id: str,
    source_id: str,
    source_type: str,
    polarity: str,
    *,
    issue_key: str = "transmission_shift_behavior",
    resolved_reports: int = 0,
    corroborated: int = 0,
    contradicted: int = 0,
    dependency_group: str | None = None,
):
    return EvidenceRecord(
        evidence_id=evidence_id,
        issue_key=issue_key,
        source_id=source_id,
        source_type=source_type,
        polarity=polarity,
        observed_at=date(2026, 9, 20),
        text=evidence_id,
        source_history=SourceHistory(
            source_id=source_id,
            source_type=source_type,
            resolved_reports=resolved_reports,
            corroborated=corroborated,
            contradicted=contradicted,
        ),
        dependency_group=dependency_group,
    )


def test_source_prior_is_used_without_history(service):
    assert service.effective_reliability("owner") == pytest.approx(0.35)
    assert service.effective_reliability("inspector") == pytest.approx(0.85)


def test_small_history_blends_with_prior(service):
    value = service.effective_reliability(
        "mechanic",
        SourceHistory("src-1", "mechanic", resolved_reports=1, corroborated=1),
    )
    historical = 5 / 7
    expected = (1 - 1 / 6) * 0.75 + (1 / 6) * historical
    assert value == pytest.approx(expected)


def test_repeated_same_source_is_not_independent(service):
    result = service.classify(
        "transmission_shift_behavior",
        [
            evidence("e1", "mechanic-1", "mechanic", "supporting"),
            evidence("e2", "mechanic-1", "mechanic", "supporting"),
        ],
    )
    assert result.independent_supporting_sources == 1
    assert result.support_weight == pytest.approx(0.75)


def test_independent_sources_add_support(service):
    result = service.classify(
        "transmission_shift_behavior",
        [
            evidence("e1", "mechanic-1", "mechanic", "supporting"),
            evidence("e2", "inspector-1", "inspector", "supporting"),
        ],
    )
    assert result.independent_supporting_sources == 2
    assert result.support_weight == pytest.approx(1.60)
    assert result.confidence is not None


def test_contradiction_is_preserved_and_affects_direction(service):
    result = service.classify(
        "transmission_shift_behavior",
        [
            evidence("e1", "mechanic-1", "mechanic", "supporting"),
            evidence("e2", "owner-1", "owner", "contradicting"),
        ],
    )
    assert len(result.supporting_evidence) == 1
    assert len(result.contradicting_evidence) == 1
    assert result.contradiction_weight == pytest.approx(0.35)
    assert result.confidence is not None


def test_unresolved_evidence_does_not_create_direction(service):
    result = service.classify(
        "transmission_shift_behavior",
        [evidence("e1", "owner-1", "owner", "unresolved")],
    )
    assert result.confidence is None
    assert result.state == "insufficient_evidence"
    assert len(result.unresolved_evidence) == 1


def test_dependency_group_prevents_double_counting(service):
    result = service.classify(
        "transmission_shift_behavior",
        [
            evidence("e1", "mechanic-1", "mechanic", "supporting", dependency_group="copy-1"),
            evidence("e2", "inspector-1", "inspector", "supporting", dependency_group="copy-1"),
        ],
    )
    assert result.independent_supporting_sources == 1
    assert result.support_weight == pytest.approx(0.75)


def test_unrelated_issue_is_ignored(service):
    result = service.classify(
        "transmission_shift_behavior",
        [evidence("e1", "mechanic-1", "mechanic", "supporting", issue_key="brake_noise")],
    )
    assert result.confidence is None
    assert result.state == "insufficient_evidence"


def test_invalid_source_history_is_rejected(service):
    with pytest.raises(ValueError):
        service.effective_reliability(
            "mechanic",
            SourceHistory("src-1", "mechanic", resolved_reports=1, corroborated=2),
        )
