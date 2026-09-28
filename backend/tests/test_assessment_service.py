import pytest

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


@pytest.mark.asyncio
async def test_assessment_uses_explicit_source_outcomes_for_reliability():
    class Memory:
        async def recall_vehicle_history(self, vehicle_id, query):
            return [
                MemoryEvidence(
                    memory_id="vehicle-report",
                    text="Transmission hesitation.",
                    metadata={
                        "report_id": "RPT-CURRENT",
                        "source_id": "SRC-1",
                        "source_type": "mechanic",
                        "issue_candidate": "transmission_shift_behavior",
                        "polarity": "supporting",
                        "observed_at": "2026-09-20",
                    },
                )
            ]

        async def recall_source_history(self, source_id, query):
            assert source_id == "SRC-1"
            return [
                MemoryEvidence(
                    memory_id="outcome-1",
                    text="Report RPT-OLD was later corroborated.",
                    metadata={
                        "resolved_report_id": "RPT-OLD",
                        "resolution_status": "corroborated",
                        "resolved_at": "2026-08-01T00:00:00Z",
                    },
                ),
                MemoryEvidence(
                    memory_id="outcome-2",
                    text="Report RPT-OLD was later contradicted.",
                    metadata={
                        "resolved_report_id": "RPT-OLD",
                        "resolution_status": "contradicted",
                        "resolved_at": "2026-09-01T00:00:00Z",
                    },
                ),
                MemoryEvidence(
                    memory_id="outcome-3",
                    text="Report RPT-OLDER was corroborated.",
                    metadata={
                        "source_id": "SRC-1",
                        "resolved_report_id": "RPT-OLDER",
                        "resolution_status": "corroborated",
                        "resolved_at": "2026-07-01T00:00:00Z",
                    },
                ),
                MemoryEvidence(
                    memory_id="outcome-other-source",
                    text="A different source's report was corroborated.",
                    metadata={
                        "source_id": "SRC-OTHER",
                        "resolved_report_id": "RPT-OTHER",
                        "resolution_status": "corroborated",
                        "resolved_at": "2026-09-10T00:00:00Z",
                    },
                ),
            ]

    assessment, state = await AssessmentService().assess_vehicle(
        vehicle_id="VEH-1",
        issue_key="transmission_shift_behavior",
        memory_service=Memory(),
    )

    # The most recent explicit resolution for RPT-OLD wins; its claim polarity
    # is not treated as an outcome about source reliability.
    assert state == "available"
    assert assessment.supporting_evidence[0].effective_reliability == pytest.approx(
        (5 / 7) * 0.75 + (2 / 7) * (5 / 7)
    )
