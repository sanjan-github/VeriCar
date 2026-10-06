from __future__ import annotations

import asyncio
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app, get_database, get_memory_service
from backend.app.models.memory import VehicleReport
from backend.app.models.report import ReportSubmission
from backend.tests.test_report_ingestion import FakeMemoryService, make_app
from core.database import Database
from core.models import Car


def test_fix1_unknown_vehicle_assessment_returns_404(tmp_path):
    """FIX 1: Unknown vehicle assessment returns 404 VEHICLE_NOT_FOUND."""
    db = Database(tmp_path / "test.db")
    memory = FakeMemoryService()

    app.dependency_overrides[get_memory_service] = lambda: memory
    app.dependency_overrides[get_database] = lambda: db

    try:
        with TestClient(app) as client:
            res = client.get("/api/vehicles/VEH-UNKNOWN-999/assessment")
            assert res.status_code == 404
            body = res.json()
            assert body["detail"]["error"]["code"] == "VEHICLE_NOT_FOUND"

            res_exp = client.get("/api/vehicles/VEH-UNKNOWN-999/assessment/explanation")
            assert res_exp.status_code == 404
            body_exp = res_exp.json()
            assert body_exp["detail"]["error"]["code"] == "VEHICLE_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


def test_fix1_known_vehicle_without_history_returns_valid_empty_assessment(tmp_path):
    """FIX 1: Known vehicle with no history returns 200 with empty memory_status."""
    db = Database(tmp_path / "test.db")
    car = Car(car_id="VEH-KNOWN-001", brand="Tata", model="Nexon", manufacture_year=2022)
    db.save_car(car)

    memory = FakeMemoryService()
    app.dependency_overrides[get_memory_service] = lambda: memory
    app.dependency_overrides[get_database] = lambda: db

    try:
        with TestClient(app) as client:
            res = client.get("/api/vehicles/VEH-KNOWN-001/assessment")
            assert res.status_code == 200
            body = res.json()
            assert body["vehicle_id"] == "VEH-KNOWN-001"
            assert body["memory_status"] == "empty"
    finally:
        app.dependency_overrides.clear()


def test_fix2_empty_hindsight_with_durable_history(tmp_path):
    """FIX 2: Empty Hindsight recall returns memory_status 'empty' (200 OK) rather than 503."""
    db = Database(tmp_path / "test.db")
    car = Car(car_id="VEH-DURABLE-01", brand="Toyota", model="City", manufacture_year=2020)
    db.save_car(car)

    memory = FakeMemoryService()
    # FakeMemoryService recall returns [] by default when no memories added

    app.dependency_overrides[get_memory_service] = lambda: memory
    app.dependency_overrides[get_database] = lambda: db

    try:
        with TestClient(app) as client:
            res = client.get("/api/vehicles/VEH-DURABLE-01/assessment")
            assert res.status_code == 200
            assert res.json()["memory_status"] == "empty"
    finally:
        app.dependency_overrides.clear()


def test_fix2_frontend_wording_clarification():
    """FIX 2: Verify app.js memoryStatusCopy does not use ambiguous 'No matching history'."""
    app_js_path = Path("frontend/app.js")
    code = app_js_path.read_text(encoding="utf-8")
    assert '"No matching history"' not in code
    assert '"No matching assessment evidence"' in code


def test_fix3_frontend_reloads_history_on_failed_report_submission():
    """FIX 3: Verify app.js report submission reloads vehicle history on error."""
    js_test_script = """
const fs = require('fs');

class Element {
  constructor(tagName) {
    this.tagName = tagName;
    this.value = '';
    this.textContent = '';
    this.hidden = false;
    this.disabled = false;
    this.dataset = {};
    this.listeners = {};
    this.attributes = {};
  }
  addEventListener(event, fn) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(fn);
  }
  reset() {
    this.value = '';
    this.dispatchEvent({ type: 'reset', preventDefault: () => {} });
  }
  setAttribute(k, v) { this.attributes[k] = v; }
  getAttribute(k) { return this.attributes[k]; }
  classList = { add() {}, remove() {} };
}

const elementsMap = {};
function getEl(sel) {
  if (!elementsMap[sel]) {
    elementsMap[sel] = new Element(sel.startsWith('#') ? 'div' : 'form');
  }
  return elementsMap[sel];
}

global.window = { location: { protocol: 'http:' } };
global.document = {
  querySelector: (sel) => getEl(sel)
};

const calls = [];
global.fetch = async (url, options) => {
  calls.push({ url, options });
  if (url === '/api/reports') {
    return {
      ok: false,
      headers: { get: (h) => (h.toLowerCase() === 'content-type' ? 'application/json' : null) },
      json: async () => ({
        detail: {
          error: {
            message: 'Report saved locally, but external memory processing did not complete. Retry to reconcile memory storage.'
          }
        }
      })
    };
  }
  if (url.startsWith('/api/vehicles/VEH-FIX3')) {
    return {
      ok: true,
      headers: { get: (h) => (h.toLowerCase() === 'content-type' ? 'application/json' : null) },
      json: async () => ({
        vehicle_id: 'VEH-FIX3',
        reports: [{ report_id: 'RPT-DURABLE-1', observed_at: '2026-09-20', text: 'Durable report text', source_type: 'mechanic', source_id: 'SRC-1' }]
      })
    };
  }
  return {
    ok: true,
    headers: { get: (h) => (h.toLowerCase() === 'content-type' ? 'application/json' : null) },
    json: async () => ({})
  };
};

const appCode = fs.readFileSync('frontend/app.js', 'utf8');
eval(appCode);

(async () => {
  const reportForm = getEl('#report-form');
  const reportVehicleId = getEl('#report-vehicle-id');
  const reportSourceId = getEl('#report-source-id');
  const reportSourceType = getEl('#report-source-type');
  const reportObservedAt = getEl('#report-observed-at');
  const reportText = getEl('#report-text');

  reportVehicleId.value = 'VEH-FIX3';
  reportSourceId.value = 'SRC-01';
  reportSourceType.value = 'mechanic';
  reportObservedAt.value = '2026-09-20';
  reportText.value = 'Transmission slip.';

  const event = { preventDefault() {} };
  await reportForm.listeners['submit'][0](event);

  // Fail the test explicitly if the history refresh did not happen.
  const vehicleCalls = calls.filter(c => c.url.includes('/api/vehicles/VEH-FIX3'));
  if (vehicleCalls.length < 1) {
    throw new Error('Expected vehicle history reload after report failure');
  }

  // Fail explicitly if the original report error was not preserved.
  const reportResult = getEl('#report-result');
  if (!reportResult.textContent.includes('Report saved locally')) {
    throw new Error('Expected original report error message to remain visible');
  }

  console.log('JS_FIX3_REFRESH_PASS');
})();
"""
    result = subprocess.run(
        ["node", "-e", js_test_script],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "JS_FIX3_REFRESH_PASS" in result.stdout


def test_fix4_ambiguity_aware_failure_message(tmp_path):
    """FIX 4: Report failure response uses ambiguity-aware wording."""
    db = Database(tmp_path / "test.db")
    memory = FakeMemoryService()
    memory.fail_vehicle = True

    app.dependency_overrides[get_memory_service] = lambda: memory
    app.dependency_overrides[get_database] = lambda: db

    payload = {
        "vehicle_id": "VEH-FIX4-01",
        "source_id": "SRC-001",
        "source_type": "mechanic",
        "observed_at": "2026-09-20",
        "text": "Transmission hesitation observed.",
    }

    try:
        with TestClient(app) as client:
            res = client.post(
                "/api/reports",
                json=payload,
                headers={"Idempotency-Key": "fix4-key-001"},
            )
            assert res.status_code == 503
            body = res.json()
            message = body["message"]
            assert "before any memory was recorded" not in message
            assert "Report saved locally, but external memory processing did not complete." in message
            assert "Retry to reconcile memory storage." in message

            # Also verify report remains stored durably in SQLite
            row = db.get_api_report(body["report_id"])
            assert row is not None
            assert row["vehicle_id"] == "VEH-FIX4-01"
    finally:
        app.dependency_overrides.clear()


def test_hindsight_failure_preserves_durable_history_endpoint(tmp_path):
    """FIX 5-D: Hindsight failure causes assessment 503 while GET /api/vehicles/{id} remains 200."""
    db = Database(tmp_path / "test.db")
    car = Car(car_id="VEH-DURABLE-FAIL", brand="Honda", model="Civic", manufacture_year=2021)
    db.save_car(car)

    class FailingMemoryService(FakeMemoryService):
        async def recall_vehicle_history(self, vehicle_id: str, query: str) -> Any:
            raise RuntimeError("Hindsight connection refused")

    memory = FailingMemoryService()
    app.dependency_overrides[get_memory_service] = lambda: memory
    app.dependency_overrides[get_database] = lambda: db

    try:
        with TestClient(app) as client:
            # Durable history endpoint remains 200 OK
            history_res = client.get("/api/vehicles/VEH-DURABLE-FAIL")
            assert history_res.status_code == 200
            assert history_res.json()["vehicle_id"] == "VEH-DURABLE-FAIL"

            # Assessment endpoint returns 503 MEMORY_UNAVAILABLE
            assess_res = client.get("/api/vehicles/VEH-DURABLE-FAIL/assessment")
            assert assess_res.status_code == 503
            assert assess_res.json()["detail"]["error"]["code"] == "MEMORY_UNAVAILABLE"
    finally:
        app.dependency_overrides.clear()
