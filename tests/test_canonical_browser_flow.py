from pathlib import Path


FRONTEND_APP = Path(__file__).resolve().parents[1] / "frontend" / "app.js"


def test_browser_loads_durable_vehicle_history_before_memory_assessment():
    source = FRONTEND_APP.read_text(encoding="utf-8")

    history_call = '"/api/vehicles/" + encodeURIComponent(vehicleId),'
    assessment_call = '"/api/vehicles/" + encodeURIComponent(vehicleId) +\n        "/assessment/explanation?issue=transmission_shift_behavior",'

    assert history_call in source
    assert assessment_call in source
    assert source.index(history_call) < source.index(assessment_call)


def test_browser_keeps_local_history_visible_when_memory_assessment_is_unavailable():
    source = FRONTEND_APP.read_text(encoding="utf-8")

    assert "state.history = history;" in source
    assert "Local history available · assessment unavailable" in source
    assert "renderHistory(history);" in source
    assert "The durable vehicle history is available" in source


def test_browser_keeps_idempotent_report_submission_in_canonical_flow():
    source = FRONTEND_APP.read_text(encoding="utf-8")

    assert '"Idempotency-Key": idempotencyKey' in source
    assert 'await loadVehicle(state.vehicleId);' in source


def test_browser_uses_same_origin_api_routes():
    source = FRONTEND_APP.read_text(encoding="utf-8")

    assert 'fetchJson("/health"' in source
    assert '"/api/vehicles/"' in source
    assert 'fetchJson("/api/reports"' in source
    assert "localhost:8000" not in source
