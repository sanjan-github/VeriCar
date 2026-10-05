from pathlib import Path


FRONTEND_APP = Path(__file__).resolve().parents[1] / "frontend" / "app.js"


def test_browser_report_submission_sends_idempotency_key():
    source = FRONTEND_APP.read_text(encoding="utf-8")

    assert '"Idempotency-Key": idempotencyKey' in source
    assert "const idempotencyKey = getIdempotencyKey();" in source


def test_browser_retries_reuse_key_until_form_reset():
    source = FRONTEND_APP.read_text(encoding="utf-8")

    assert "function getIdempotencyKey()" in source
    assert "elements.reportForm.dataset.idempotencyKey" in source
    assert 'elements.reportForm.addEventListener("reset"' in source
    assert "delete elements.reportForm.dataset.idempotencyKey;" in source


def test_browser_has_uuid_generation_with_fallback():
    source = FRONTEND_APP.read_text(encoding="utf-8")

    assert 'crypto.randomUUID()' in source
    assert 'return "idem-" + Date.now()' in source
