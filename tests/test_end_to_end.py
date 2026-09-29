from __future__ import annotations

from datetime import date
from io import BytesIO

import pytest
from pypdf import PdfReader

from core.assessment_pipeline import run_assessment
from core.database import Database
from core.demo_scenarios import build_demo_scenarios, get_demo_scenario
from core.memory_recall import recall_vehicle_memory
from core.memory_sync import sync_condition_to_memory
from core.models import Car
from core.pdf_report import build_assessment_pdf
from core.groq_llm import LLMExplanation
from memory.hindsight import MemoryItem


class FakeLLM:
    def explain(self, evidence):
        assert evidence["deterministic_assessment"]["verdict"] in {
            "BUY",
            "NEGOTIATE",
            "AVOID",
        }
        return LLMExplanation(
            summary="Evidence was reviewed without changing the deterministic assessment.",
            evidence_explanations=["The explanation is grounded in supplied evidence."],
            contradictions=[],
            ai_estimates=[],
        )


class FailingLLM:
    def explain(self, evidence):
        raise RuntimeError("Groq unavailable")


class FakeMemory:
    retained: list[dict] = []

    async def retain_vehicle_report(self, **kwargs):
        self.retained.append(kwargs)

    async def recall_vehicle(self, *, vehicle_id, query):
        return [
            MemoryItem(
                memory_id=f"memory-{vehicle_id}",
                text=f"Historical evidence for {vehicle_id}: {query}",
                metadata={"vehicle_id": vehicle_id},
                tags=[f"vehicle:{vehicle_id}"],
            )
        ]


class FailingMemory:
    async def retain_vehicle_report(self, **kwargs):
        raise RuntimeError("Hindsight unavailable")


def test_end_to_end_success_persists_assesses_explains_recalls_and_builds_pdf(
    tmp_path, monkeypatch
):
    scenario = get_demo_scenario("clean")
    db = Database(tmp_path / "vericar.db")

    db.save_car(scenario.car)
    db.save_condition(scenario.condition)

    fake_memory = FakeMemory()
    monkeypatch.setattr("core.memory_sync.HindsightMemory", lambda: fake_memory)
    report_id, memory_error = sync_condition_to_memory(
        scenario.car, scenario.condition, db
    )

    assert memory_error is None
    assert report_id.startswith("RPT-")
    assert db.get_condition(scenario.car.car_id) is not None
    assert db.get_memory_report(report_id)["status"] == "synced"
    assert fake_memory.retained[0]["vehicle_id"] == scenario.car.car_id

    monkeypatch.setattr("core.memory_recall.HindsightMemory", lambda: fake_memory)
    memory_result = recall_vehicle_memory(
        scenario.car, query="repairs and service history"
    )
    assert memory_result.status == "AVAILABLE"
    assert len(memory_result.items) == 1
    assert memory_result.items[0].metadata["vehicle_id"] == scenario.car.car_id

    result = run_assessment(
        scenario.car,
        db.get_condition(scenario.car.car_id),
        db,
        today=date(2026, 9, 29),
        generate_explanation=True,
        llm=FakeLLM(),
    )

    assert result.assessment is not None
    assert result.assessment.verdict == "BUY"
    assert result.explanation is not None
    assert result.explanation.llm.summary

    pdf = build_assessment_pdf(
        scenario.car,
        scenario.condition,
        result,
        generated_at=date(2026, 9, 29),
    )
    reader = PdfReader(BytesIO(pdf))
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "VeriCar Assessment Report" in pdf_text
    assert scenario.car.car_id in pdf_text
    assert "BUY" in pdf_text


@pytest.mark.parametrize("scenario_key", ["clean", "negotiate", "critical"])
def test_all_demo_scenarios_survive_persistence_to_assessment_and_pdf(
    tmp_path, scenario_key
):
    scenario = next(
        item for item in build_demo_scenarios() if item.key == scenario_key
    )
    db = Database(tmp_path / f"{scenario_key}.db")

    db.save_car(scenario.car)
    db.save_condition(scenario.condition)

    persisted_condition = db.get_condition(scenario.car.car_id)
    assert persisted_condition is not None
    assert persisted_condition.car_id == scenario.car.car_id

    result = run_assessment(
        scenario.car,
        persisted_condition,
        db,
        today=date(2026, 9, 29),
    )

    assert result.assessment is not None

    pdf = build_assessment_pdf(scenario.car, persisted_condition, result)
    reader = PdfReader(BytesIO(pdf))
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert scenario.car.car_id in pdf_text
    assert result.assessment.verdict in pdf_text


def test_end_to_end_external_failures_preserve_local_assessment(tmp_path, monkeypatch):
    scenario = get_demo_scenario("critical")
    db = Database(tmp_path / "failure.db")
    db.save_car(scenario.car)
    db.save_condition(scenario.condition)

    monkeypatch.setattr("core.memory_sync.HindsightMemory", FailingMemory)
    report_id, memory_error = sync_condition_to_memory(
        scenario.car, scenario.condition, db
    )

    assert report_id.startswith("RPT-")
    assert "Hindsight unavailable" in memory_error
    assert db.get_condition(scenario.car.car_id) is not None
    assert db.get_memory_report(report_id)["status"] == "failed"

    result = run_assessment(
        scenario.car,
        db.get_condition(scenario.car.car_id),
        db,
        today=date(2026, 9, 29),
        generate_explanation=True,
        llm=FailingLLM(),
    )

    assert result.assessment is not None
    assert result.assessment.verdict == "AVOID"
    assert result.explanation is None


def test_unknown_evidence_reduces_confidence_without_blocking_end_to_end_assessment(
    tmp_path,
):
    car = Car(
        car_id="E2E-UNKNOWN",
        brand="Tata",
        model="Nexon",
        manufacture_year=2022,
        variant="XZ+",
        fuel_type="Petrol",
        transmission="Manual",
        odometer_km=30_000,
    )
    from core.condition import ConditionRecord

    condition = ConditionRecord.empty(car.car_id)
    db = Database(tmp_path / "unknown.db")

    result = run_assessment(
        car,
        condition,
        db,
        today=date(2026, 9, 29),
    )

    assert result.assessment is not None
    assert result.assessment.confidence < 90
    assert result.assessment.verdict in {"BUY", "NEGOTIATE", "AVOID"}
