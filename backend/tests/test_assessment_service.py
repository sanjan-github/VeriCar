from backend.app.models.memory import MemoryEvidence
from backend.app.services.assessment_service import AssessmentService


def test_recalled_memory_becomes_traceable_evidence_record():
    item = MemoryEvidence(
        memory_id="memory-1",
        text="Hard shifting into third.",
        metadata={
            "report_id": "RPT-1",
            "source_id": "SRC-1",
            "source_type": "inspector",
            "issue_candidate": "transmission_shift_behavior",
            "polarity": "supporting",
            "observed_at": "2026-09-20T00:00:00+00:00",
        },
    )

    record = AssessmentService._to_evidence_record(item)

    assert record.evidence_id == "memory-1"
    assert record.issue_key == "transmission_shift_behavior"
    assert record.source_id == "SRC-1"
    assert record.source_type == "inspector"
    assert record.polarity == "supporting"
    assert record.observed_at.isoformat() == "2026-09-20"


def test_memory_without_claim_metadata_is_unresolved_and_unmatched():
    record = AssessmentService._to_evidence_record(
        MemoryEvidence(memory_id="memory-2", text="A general observation.")
    )

    assert record.issue_key == "unknown"
    assert record.polarity == "unresolved"
