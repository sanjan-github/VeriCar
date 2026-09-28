import json

import httpx
import pytest

from backend.app.models.evidence import Assessment, EvidenceContribution
from backend.app.services.groq_explanation_service import GroqExplanationService


def _assessment() -> Assessment:
    return Assessment(
        issue_key="transmission_shift_behavior",
        state="moderate_evidence",
        confidence=62.0,
        support_weight=1.6,
        contradiction_weight=0.35,
        independent_supporting_sources=2,
        independent_contradicting_sources=1,
        supporting_evidence=(
            EvidenceContribution(
                evidence_id="memory-1",
                source_id="SRC-1",
                source_type="mechanic",
                polarity="supporting",
                effective_reliability=0.75,
                observed_at=__import__("datetime").date(2026, 9, 20),
                text="Hesitation between second and third gear.",
            ),
        ),
        contradicting_evidence=(),
        unresolved_evidence=(),
    )


@pytest.mark.asyncio
async def test_groq_explanation_validates_returned_evidence_ids(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "The available evidence indicates moderate concern.",
                                    "rationale": "A mechanic reported hesitation.",
                                    "caveats": ["The evidence does not establish a mechanical diagnosis."],
                                    "evidence_ids": ["memory-1"],
                                }
                            )
                        }
                    }
                ]
            },
        )

    service = GroqExplanationService(
        api_key="test-key",
        model="test-model",
        base_url="https://example.test",
        timeout=5,
    )
    transport = httpx.MockTransport(handler)

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )
    result = await service.explain(_assessment())

    assert result.evidence_ids == ["memory-1"]
    assert captured["body"]["temperature"] == 0
    assert captured["body"]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_groq_explanation_rejects_unknown_evidence_id(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "Summary.",
                                    "rationale": "Rationale.",
                                    "caveats": [],
                                    "evidence_ids": ["not-real"],
                                }
                            )
                        }
                    }
                ]
            },
        )

    service = GroqExplanationService(
        api_key="test-key",
        model="test-model",
        base_url="https://example.test",
    )
    transport = httpx.MockTransport(handler)

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )
    with pytest.raises(ValueError, match="evidence ID"):
        await service.explain(_assessment())
