from core.data_source import DataSource, ProviderResult


def test_provider_result_separates_source_reliability_and_evidence_confidence():
    source = DataSource(
        source_id="example",
        name="Example government source",
        kind="government",
    )
    result = ProviderResult(
        status="FOUND",
        source=source,
        data={"fact": "observed"},
        source_reliability="high",
        evidence_confidence="low",
        evidence_scope="model",
    )

    assert result.source_reliability == "high"
    assert result.evidence_confidence == "low"
    assert result.evidence_scope == "model"
    assert result.available is True
    assert result.found is True


def test_provider_result_unavailable_is_not_no_data():
    source = DataSource(
        source_id="example",
        name="Example source",
        kind="official",
    )
    result = ProviderResult(
        status="UNAVAILABLE",
        source=source,
        message="timeout",
    )

    assert result.available is False
    assert result.found is False
    assert result.data is None
