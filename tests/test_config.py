import pytest

from core.config import env_float, env_int, env_url


def test_env_float_rejects_invalid_value(monkeypatch):
    monkeypatch.setenv("TEST_TIMEOUT", "not-a-number")
    with pytest.raises(ValueError, match="TEST_TIMEOUT"):
        env_float("TEST_TIMEOUT", 30.0)


def test_env_float_rejects_non_positive_value(monkeypatch):
    monkeypatch.setenv("TEST_TIMEOUT", "0")
    with pytest.raises(ValueError, match="greater than"):
        env_float("TEST_TIMEOUT", 30.0)


def test_env_int_rejects_negative_value(monkeypatch):
    monkeypatch.setenv("TEST_RETRIES", "-1")
    with pytest.raises(ValueError, match="at least 0"):
        env_int("TEST_RETRIES", 2)


def test_env_url_rejects_non_http_url(monkeypatch):
    monkeypatch.setenv("TEST_URL", "file:///tmp/vericar")
    with pytest.raises(ValueError, match="HTTP"):
        env_url("TEST_URL", "http://localhost:8888")
