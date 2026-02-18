"""Tests for LLM service: connectivity test, session helpers, and guards."""

from unittest.mock import MagicMock

import httpx
import pytest
from litestar.exceptions import NotAuthorizedException

from easyorario.exceptions import LLMConfigError
from easyorario.guards.auth import requires_llm_config
from easyorario.services.llm import LLMService, get_llm_config


class TestLLMConfigError:
    def test_llm_config_error_stores_error_key(self):
        exc = LLMConfigError("llm_connection_failed")
        assert exc.error_key == "llm_connection_failed"

    def test_llm_config_error_is_easyorario_error(self):
        from easyorario.exceptions import EasyorarioError

        exc = LLMConfigError("llm_timeout")
        assert isinstance(exc, EasyorarioError)


class TestLLMServiceConnectivity:
    """Test LLMService.test_connectivity with mocked httpx responses."""

    async def test_connectivity_with_reachable_endpoint_succeeds(self, monkeypatch):
        async def mock_get(self, url, **kwargs):
            return httpx.Response(200, json={"data": [{"id": "gpt-4o"}]})

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        service = LLMService()
        await service.test_connectivity("https://api.openai.com", "sk-valid", "gpt-4o")

    async def test_connectivity_with_unreachable_url_raises(self, monkeypatch):
        async def mock_get(self, url, **kwargs):
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        service = LLMService()
        with pytest.raises(LLMConfigError, match="llm_connection_failed"):
            await service.test_connectivity("https://bad.example.com", "sk-valid", "gpt-4o")

    async def test_connectivity_with_bad_api_key_raises(self, monkeypatch):
        async def mock_get(self, url, **kwargs):
            return httpx.Response(401, json={"error": "invalid_api_key"})

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        service = LLMService()
        with pytest.raises(LLMConfigError, match="llm_auth_failed"):
            await service.test_connectivity("https://api.openai.com", "sk-bad", "gpt-4o")

    async def test_connectivity_with_forbidden_raises(self, monkeypatch):
        async def mock_get(self, url, **kwargs):
            return httpx.Response(403, json={"error": "forbidden"})

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        service = LLMService()
        with pytest.raises(LLMConfigError, match="llm_auth_failed"):
            await service.test_connectivity("https://api.openai.com", "sk-bad", "gpt-4o")

    async def test_connectivity_with_timeout_raises(self, monkeypatch):
        async def mock_get(self, url, **kwargs):
            raise httpx.ReadTimeout("Timed out")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        service = LLMService()
        with pytest.raises(LLMConfigError, match="llm_timeout"):
            await service.test_connectivity("https://slow.example.com", "sk-valid", "gpt-4o")

    async def test_connectivity_with_server_error_raises(self, monkeypatch):
        async def mock_get(self, url, **kwargs):
            return httpx.Response(500, text="Internal Server Error")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        service = LLMService()
        with pytest.raises(LLMConfigError, match="llm_connection_failed"):
            await service.test_connectivity("https://api.openai.com", "sk-valid", "gpt-4o")

    async def test_connectivity_normalizes_trailing_slash(self, monkeypatch):
        captured_url = None

        async def mock_get(self, url, **kwargs):
            nonlocal captured_url
            captured_url = url
            return httpx.Response(200, json={"data": []})

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        service = LLMService()
        await service.test_connectivity("https://api.openai.com/v1/", "sk-valid", "gpt-4o")
        assert captured_url == "https://api.openai.com/v1/models"


class TestGetLLMConfig:
    def test_get_llm_config_returns_none_when_not_set(self):
        session: dict[str, str] = {"user_id": "123", "email": "a@b.com", "role": "responsible_professor"}
        assert get_llm_config(session) is None

    def test_get_llm_config_returns_dict_when_set(self):
        session = {
            "user_id": "123",
            "llm_base_url": "https://api.openai.com",
            "llm_api_key": "sk-test",
            "llm_model_id": "gpt-4o",
        }
        config = get_llm_config(session)
        assert config is not None
        assert config["base_url"] == "https://api.openai.com"
        assert config["api_key"] == "sk-test"
        assert config["model_id"] == "gpt-4o"

    def test_get_llm_config_returns_none_when_base_url_missing(self):
        session = {"llm_api_key": "sk-test", "llm_model_id": "gpt-4o"}
        assert get_llm_config(session) is None

    def test_get_llm_config_returns_none_when_api_key_missing(self):
        session = {"llm_base_url": "https://api.openai.com", "llm_model_id": "gpt-4o"}
        assert get_llm_config(session) is None

    def test_get_llm_config_with_empty_model_id_returns_empty_string(self):
        session = {
            "llm_base_url": "https://api.openai.com",
            "llm_api_key": "sk-test",
        }
        config = get_llm_config(session)
        assert config is not None
        assert config["model_id"] == ""


class TestRequiresLLMConfigGuard:
    """Test the requires_llm_config guard function."""

    def _make_connection(self, session: dict):
        """Create a minimal mock connection with a session dict."""
        conn = MagicMock()
        conn.session = session
        return conn

    def test_requires_llm_config_passes_when_configured(self):
        conn = self._make_connection(
            {
                "llm_base_url": "https://api.openai.com",
                "llm_api_key": "sk-test",
                "llm_model_id": "gpt-4o",
            }
        )
        requires_llm_config(conn, MagicMock())  # should not raise

    def test_requires_llm_config_raises_when_not_configured(self):
        conn = self._make_connection({"user_id": "123", "email": "a@b.com", "role": "responsible_professor"})
        with pytest.raises(NotAuthorizedException):
            requires_llm_config(conn, MagicMock())

    def test_requires_llm_config_raises_when_partial_config(self):
        conn = self._make_connection({"llm_base_url": "https://api.openai.com"})
        with pytest.raises(NotAuthorizedException):
            requires_llm_config(conn, MagicMock())
