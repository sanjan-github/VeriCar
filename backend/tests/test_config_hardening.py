from __future__ import annotations

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.app.config import (
    ConfigurationError,
    Settings,
    env_bool,
    env_float,
    env_int,
    env_str,
    env_url,
)
from backend.app.main import (
    app,
    get_database,
    get_groq_explanation_service,
    get_memory_service,
)
from backend.app.models.memory import MemoryEvidence
from backend.tests.test_report_ingestion import FakeMemoryService
from core.database import Database
from core.models import Car


def memory(*, memory_id: str, text: str, metadata: dict) -> MemoryEvidence:
    return MemoryEvidence(
        memory_id=memory_id,
        text=text,
        metadata=metadata,
        tags=[],
        mentioned_at="2026-09-20T00:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# 1. Configuration Validation Tests
# ---------------------------------------------------------------------------


def test_valid_default_config_loads_successfully():
    cfg = Settings(env={})
    assert cfg.app_name == "VeriCar"
    assert cfg.app_env == "development"
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8000
    assert cfg.hindsight_base_url == ""
    assert cfg.hindsight_timeout == 30.0
    assert cfg.hindsight_startup_check is False
    assert cfg.groq_base_url == "https://api.groq.com/openai/v1"
    assert cfg.groq_model == "llama-3.3-70b-versatile"
    assert cfg.groq_timeout == 20.0
    assert cfg.db_path == "data/vericar.db"


@pytest.mark.parametrize("invalid_port", ["abc", "-1", "0", "65536", "70000", "8000.5"])
def test_invalid_port_raises_configuration_error(invalid_port: str):
    with pytest.raises(ConfigurationError, match="PORT"):
        Settings(env={"PORT": invalid_port})


@pytest.mark.parametrize("invalid_timeout", ["abc", "-5", "-0.1", "0"])
def test_invalid_hindsight_timeout_raises_configuration_error(invalid_timeout: str):
    with pytest.raises(ConfigurationError, match="HINDSIGHT_TIMEOUT"):
        Settings(env={"HINDSIGHT_TIMEOUT": invalid_timeout})


@pytest.mark.parametrize("invalid_timeout", ["abc", "-1", "0", "none"])
def test_invalid_groq_timeout_raises_configuration_error(invalid_timeout: str):
    with pytest.raises(ConfigurationError, match="GROQ_TIMEOUT"):
        Settings(env={"GROQ_TIMEOUT": invalid_timeout})


@pytest.mark.parametrize(
    "invalid_url",
    ["ftp://vectorize.io", "not-a-url", "http://", "https://", "localhost:8888", "file:///tmp/db"],
)
def test_invalid_base_urls_raise_configuration_error(invalid_url: str):
    with pytest.raises(ConfigurationError, match="HINDSIGHT_BASE_URL"):
        Settings(env={"HINDSIGHT_BASE_URL": invalid_url})

    with pytest.raises(ConfigurationError, match="GROQ_BASE_URL"):
        Settings(env={"GROQ_BASE_URL": invalid_url})


def test_config_helper_functions():
    # env_str
    assert env_str("TEST_STR", "default", env={}) == "default"
    assert env_str("TEST_STR", "default", env={"TEST_STR": "custom"}) == "custom"
    with pytest.raises(ConfigurationError, match="TEST_STR"):
        env_str("TEST_STR", "a", env={"TEST_STR": "c"}, allowed={"a", "b"})

    # env_int
    assert env_int("TEST_INT", 10, env={}) == 10
    assert env_int("TEST_INT", 10, env={"TEST_INT": "20"}, min_value=5, max_value=25) == 20
    with pytest.raises(ConfigurationError, match="TEST_INT"):
        env_int("TEST_INT", 10, env={"TEST_INT": "4"}, min_value=5)
    with pytest.raises(ConfigurationError, match="TEST_INT"):
        env_int("TEST_INT", 10, env={"TEST_INT": "30"}, max_value=25)

    # env_float
    assert env_float("TEST_FLOAT", 1.5, env={}) == 1.5
    assert env_float("TEST_FLOAT", 1.5, env={"TEST_FLOAT": "2.5"}, min_value=1.0, max_value=3.0) == 2.5
    with pytest.raises(ConfigurationError, match="TEST_FLOAT"):
        env_float("TEST_FLOAT", 1.5, env={"TEST_FLOAT": "0.5"}, min_value=1.0)

    # env_bool
    assert env_bool("TEST_BOOL", True, env={}) is True
    assert env_bool("TEST_BOOL", False, env={"TEST_BOOL": "true"}) is True
    assert env_bool("TEST_BOOL", True, env={"TEST_BOOL": "0"}) is False
    with pytest.raises(ConfigurationError, match="TEST_BOOL"):
        env_bool("TEST_BOOL", True, env={"TEST_BOOL": "maybe"})


# ---------------------------------------------------------------------------
# 2. Dependency Failure and Resilience Tests
# ---------------------------------------------------------------------------


def test_missing_groq_api_key_results_in_unavailable_explanation_without_crashing(tmp_path):
    """Missing GROQ_API_KEY leaves deterministic assessment intact with explanation_status='unavailable'."""
    db = Database(tmp_path / "test.db")
    db.save_car(Car(car_id="VEH-CFG-001", brand="Hyundai", model="Creta", manufacture_year=2021))

    memory_service = FakeMemoryService()
    app.dependency_overrides[get_memory_service] = lambda: memory_service
    app.dependency_overrides[get_database] = lambda: db

    try:
        with patch("backend.app.main.get_groq_explanation_service") as mock_groq_factory:
            from backend.app.services.groq_explanation_service import GroqExplanationService

            # Configure an unconfigured groq service (empty api key)
            unconfigured_groq = GroqExplanationService(api_key="")
            mock_groq_factory.return_value = unconfigured_groq

            with TestClient(app) as client:
                res = client.get("/api/vehicles/VEH-CFG-001/assessment/explanation")
                assert res.status_code == 200
                data = res.json()
                assert data["vehicle_id"] == "VEH-CFG-001"
                assert data["explanation_status"] == "unavailable"
                assert data["explanation"] is None
                assert "findings" in data
    finally:
        app.dependency_overrides.clear()


def test_groq_upstream_failure_leaves_deterministic_assessment_intact(tmp_path):
    """Upstream Groq failure does not fail the assessment endpoint."""
    db = Database(tmp_path / "test.db")
    db.save_car(Car(car_id="VEH-CFG-002", brand="Honda", model="City", manufacture_year=2020))

    class MockFailingGroqService:
        async def explain(self, assessment):
            raise RuntimeError("Upstream 503 Service Unavailable from Groq")

    app.dependency_overrides[get_database] = lambda: db
    app.dependency_overrides[get_memory_service] = lambda: FakeMemoryService()
    app.dependency_overrides[get_groq_explanation_service] = lambda: MockFailingGroqService()

    try:
        with TestClient(app) as client:
            res = client.get("/api/vehicles/VEH-CFG-002/assessment/explanation")
            assert res.status_code == 200
            data = res.json()
            assert data["vehicle_id"] == "VEH-CFG-002"
            assert data["explanation_status"] == "unavailable"
            assert data["explanation"] is None
            assert "findings" in data
    finally:
        app.dependency_overrides.clear()


def test_hindsight_unavailable_produces_503_and_preserves_durable_sqlite_history(tmp_path, monkeypatch):
    """When Hindsight is unreachable, assessment returns 503 MEMORY_UNAVAILABLE, but SQLite history is intact."""
    db = Database(tmp_path / "test.db")
    car = Car(car_id="VEH-CFG-003", brand="Tata", model="Harrier", manufacture_year=2022)
    db.save_car(car)

    class FailingMemoryService:
        async def recall_vehicle_history(self, vin: str, query: str):
            raise ConnectionError("Hindsight server connection refused")

        async def recall_source_history(self, source_id: str, query: str):
            raise ConnectionError("Hindsight server connection refused")

    app.dependency_overrides[get_database] = lambda: db
    app.dependency_overrides[get_memory_service] = lambda: FailingMemoryService()

    try:
        monkeypatch.setattr("backend.app.main.settings.hindsight_base_url", "http://hindsight.test")
        with TestClient(app) as client:
            # 1. Assessment fails with explicit 503 MEMORY_UNAVAILABLE (not silent empty history)
            res_assessment = client.get("/api/vehicles/VEH-CFG-003/assessment")
            assert res_assessment.status_code == 503
            err = res_assessment.json()["detail"]["error"]
            assert err["code"] == "MEMORY_UNAVAILABLE"
            assert "Historical memory is temporarily unavailable" in err["message"]

            # 2. SQLite durable vehicle record remains fully accessible
            res_vehicle = client.get("/api/vehicles/VEH-CFG-003")
            assert res_vehicle.status_code == 200
            veh_data = res_vehicle.json()
            assert veh_data["vehicle_id"] == "VEH-CFG-003"
            assert veh_data["vehicle"]["brand"] == "Tata"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 3. Liveness and Readiness Tests
# ---------------------------------------------------------------------------


def test_health_endpoint_returns_200_liveness():
    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "environment" in data


def test_readiness_endpoint_when_dependencies_healthy(tmp_path, monkeypatch):
    db = Database(tmp_path / "test.db")

    class HealthyMemoryService:
        async def check_version(self):
            return "1.0.0"

    app.dependency_overrides[get_database] = lambda: db
    app.dependency_overrides[get_memory_service] = lambda: HealthyMemoryService()

    try:
        monkeypatch.setattr("backend.app.main.settings.hindsight_base_url", "http://hindsight.test")
        with TestClient(app) as client:
            res = client.get("/readiness")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "ready"
            assert data["checks"]["database"] == "available"
            assert data["checks"]["hindsight"] == "available"
    finally:
        app.dependency_overrides.clear()


def test_readiness_endpoint_reports_optional_hindsight_unavailability_without_503(tmp_path, monkeypatch):
    """Hindsight unavailability marks check as 'unavailable' but does not fail the app readiness."""
    db = Database(tmp_path / "test.db")

    class FailingMemoryService:
        async def check_version(self):
            raise ConnectionError("Hindsight offline")

    app.dependency_overrides[get_database] = lambda: db
    app.dependency_overrides[get_memory_service] = lambda: FailingMemoryService()

    try:
        monkeypatch.setattr("backend.app.main.settings.hindsight_base_url", "http://hindsight.test")
        with TestClient(app) as client:
            res = client.get("/readiness")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "ready"
            assert data["checks"]["database"] == "available"
            assert data["checks"]["hindsight"] == "unavailable"
    finally:
        app.dependency_overrides.clear()


def test_readiness_endpoint_returns_503_when_database_fails():
    """Unreachable or corrupted database causes /readiness to return 503 unready."""
    class BrokenDatabase:
        def check_connection(self):
            raise RuntimeError("Database file locked / unreachable")

    app.dependency_overrides[get_database] = lambda: BrokenDatabase()
    app.dependency_overrides[get_memory_service] = lambda: FakeMemoryService()

    try:
        with TestClient(app) as client:
            res = client.get("/readiness")
            assert res.status_code == 503
            data = res.json()
            assert data["status"] == "unready"
            assert data["checks"]["database"] == "unavailable"
    finally:
        app.dependency_overrides.clear()


def test_vercel_defaults_database_to_writable_tmp_path():
    cfg = Settings(env={"VERCEL": "1"})
    assert cfg.db_path == "/tmp/vericar.db"


def test_credential_and_database_values_are_trimmed():
    cfg = Settings(env={
        "HINDSIGHT_API_KEY": "  hindsight-key  ",
        "GROQ_API_KEY": "  groq-key  ",
        "DB_PATH": "  custom.db  ",
    })
    assert cfg.hindsight_api_key == "hindsight-key"
    assert cfg.groq_api_key == "groq-key"
    assert cfg.db_path == "custom.db"


def test_readiness_skips_hindsight_check_when_base_url_is_unconfigured(tmp_path, monkeypatch):
    db = Database(tmp_path / "test.db")

    class ExplodingMemoryService:
        async def check_version(self):
            raise AssertionError("Hindsight should not be contacted when unconfigured")

    app.dependency_overrides[get_database] = lambda: db
    app.dependency_overrides[get_memory_service] = lambda: ExplodingMemoryService()

    try:
        monkeypatch.setattr("backend.app.main.settings.hindsight_base_url", "")
        with TestClient(app) as client:
            res = client.get("/readiness")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "ready"
            assert data["checks"]["database"] == "available"
            assert data["checks"]["hindsight"] == "unconfigured"
    finally:
        app.dependency_overrides.clear()


def test_readiness_uses_public_database_connection_check():
    class BrokenDatabase:
        def check_connection(self):
            raise RuntimeError("database unavailable")

    app.dependency_overrides[get_database] = lambda: BrokenDatabase()
    app.dependency_overrides[get_memory_service] = lambda: FakeMemoryService()

    try:
        with TestClient(app) as client:
            res = client.get("/readiness")
            assert res.status_code == 503
            assert res.json()["checks"]["database"] == "unavailable"
    finally:
        app.dependency_overrides.clear()


def test_groq_malformed_json_is_rejected():
    from backend.app.models.evidence import Assessment
    from backend.app.services.groq_explanation_service import GroqExplanationService
    from unittest.mock import patch
    import asyncio

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "not-json"}}]}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return Response()

    assessment = Assessment(
        issue_key="test_issue",
        state="unknown",
        confidence=0.0,
        support_weight=0.0,
        contradiction_weight=0.0,
        independent_supporting_sources=0,
        independent_contradicting_sources=0,
        supporting_evidence=(),
        contradicting_evidence=(),
        unresolved_evidence=(),
    )
    service = GroqExplanationService(
        api_key="test-key",
        base_url="https://example.test",
    )
    with patch(
        "backend.app.services.groq_explanation_service.httpx.AsyncClient",
        return_value=Client(),
    ):
        with pytest.raises(ValueError, match="invalid explanation payload"):
            asyncio.run(service.explain(assessment))
