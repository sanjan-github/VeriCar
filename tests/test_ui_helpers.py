from app.ui_helpers import (
    history_status_copy,
    humanize_history_finding,
    verdict_copy,
)


def test_history_status_copy_distinguishes_no_history_from_unavailable():
    assert history_status_copy("NO_HISTORY")["title"] == "No previous VeriCar record found for this vehicle."
    assert history_status_copy("UNAVAILABLE")["title"] == "Vehicle history is temporarily unavailable."
    assert "could not reach" in history_status_copy("UNAVAILABLE")["body"]
    assert "does not mean" in history_status_copy("NO_HISTORY")["body"]


def test_history_status_copy_explains_contradiction_without_accusation():
    copy = history_status_copy("CONTRADICTION")
    assert copy["action"] == "Verify this before buying"
    assert "fraud" not in copy["body"].lower()


def test_humanize_history_finding_uses_buyer_language():
    finding = type(
        "Finding",
        (),
        {
            "field": "accident_status",
            "current_value": "No",
            "historical_value": "Yes",
            "kind": "CONTRADICTION",
            "message": "technical fallback",
        },
    )()
    text = humanize_history_finding(finding)
    assert "accident" in text.lower()
    assert "previous record" in text.lower()
    assert "today" in text.lower()


def test_verdict_copy_preserves_deterministic_verdict_and_plain_language():
    assert verdict_copy("BUY")["title"] == "Looks reasonable based on the information provided"
    assert verdict_copy("NEGOTIATE")["label"] == "NEGOTIATE"
    assert verdict_copy("AVOID")["title"] == "Important issues need to be resolved before buying"
