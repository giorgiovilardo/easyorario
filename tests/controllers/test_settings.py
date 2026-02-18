"""Tests for the settings controller — LLM endpoint configuration."""

from tests.conftest import _get_csrf_token


class TestGetSettings:
    async def test_get_impostazioni_renders_form(self, authenticated_client):
        response = await authenticated_client.get("/impostazioni")
        assert response.status_code == 200
        assert "base_url" in response.text
        assert "api_key" in response.text
        assert "model_id" in response.text

    async def test_get_impostazioni_as_professor_returns_403(self, authenticated_professor_client):
        response = await authenticated_professor_client.get("/impostazioni")
        assert response.status_code == 403

    async def test_post_impostazioni_as_professor_returns_403(self, authenticated_professor_client):
        csrf = _get_csrf_token(authenticated_professor_client)
        response = await authenticated_professor_client.post(
            "/impostazioni",
            data={"base_url": "https://api.openai.com", "api_key": "sk-test", "model_id": "gpt-4o"},
            headers={"x-csrftoken": csrf},
        )
        assert response.status_code == 403


class TestPostSettings:
    async def test_post_impostazioni_with_valid_config_shows_success(self, authenticated_client, monkeypatch):
        async def mock_test_connectivity(self, base_url, api_key, model_id):
            return None

        monkeypatch.setattr(
            "easyorario.services.llm.LLMService.test_connectivity",
            mock_test_connectivity,
        )

        csrf = _get_csrf_token(authenticated_client)
        response = await authenticated_client.post(
            "/impostazioni",
            data={"base_url": "https://api.openai.com", "api_key": "sk-test-key", "model_id": "gpt-4o"},
            headers={"x-csrftoken": csrf},
        )
        assert response.status_code == 200
        assert "successo" in response.text.lower()

    async def test_post_impostazioni_stores_config_in_session(self, authenticated_client, monkeypatch):
        async def mock_test_connectivity(self, base_url, api_key, model_id):
            return None

        monkeypatch.setattr(
            "easyorario.services.llm.LLMService.test_connectivity",
            mock_test_connectivity,
        )

        csrf = _get_csrf_token(authenticated_client)
        await authenticated_client.post(
            "/impostazioni",
            data={"base_url": "https://api.openai.com", "api_key": "sk-test-key", "model_id": "gpt-4o"},
            headers={"x-csrftoken": csrf},
        )
        # Verify config is in session by checking GET pre-populates
        response = await authenticated_client.get("/impostazioni")
        assert "https://api.openai.com" in response.text
        assert "gpt-4o" in response.text
        # API key must NOT be shown
        assert "sk-test-key" not in response.text

    async def test_post_impostazioni_with_unreachable_url_shows_error(self, authenticated_client, monkeypatch):
        from easyorario.exceptions import LLMConfigError

        async def mock_test_connectivity(self, base_url, api_key, model_id):
            raise LLMConfigError("llm_connection_failed")

        monkeypatch.setattr(
            "easyorario.services.llm.LLMService.test_connectivity",
            mock_test_connectivity,
        )

        csrf = _get_csrf_token(authenticated_client)
        response = await authenticated_client.post(
            "/impostazioni",
            data={"base_url": "https://bad.example.com", "api_key": "sk-test", "model_id": "gpt-4o"},
            headers={"x-csrftoken": csrf},
        )
        assert response.status_code == 200
        assert "Impossibile connettersi" in response.text

    async def test_post_impostazioni_with_empty_base_url_shows_error(self, authenticated_client):
        csrf = _get_csrf_token(authenticated_client)
        response = await authenticated_client.post(
            "/impostazioni",
            data={"base_url": "", "api_key": "sk-test", "model_id": "gpt-4o"},
            headers={"x-csrftoken": csrf},
        )
        assert response.status_code == 200
        assert "obbligatorio" in response.text.lower()

    async def test_post_impostazioni_with_empty_api_key_shows_error(self, authenticated_client):
        csrf = _get_csrf_token(authenticated_client)
        response = await authenticated_client.post(
            "/impostazioni",
            data={"base_url": "https://api.openai.com", "api_key": "", "model_id": "gpt-4o"},
            headers={"x-csrftoken": csrf},
        )
        assert response.status_code == 200
        assert "obbligatori" in response.text.lower()

    async def test_get_impostazioni_prepopulates_from_session(self, authenticated_client, monkeypatch):
        async def mock_test_connectivity(self, base_url, api_key, model_id):
            return None

        monkeypatch.setattr(
            "easyorario.services.llm.LLMService.test_connectivity",
            mock_test_connectivity,
        )

        csrf = _get_csrf_token(authenticated_client)
        await authenticated_client.post(
            "/impostazioni",
            data={"base_url": "https://api.openai.com", "api_key": "sk-test-key", "model_id": "gpt-4o"},
            headers={"x-csrftoken": csrf},
        )

        response = await authenticated_client.get("/impostazioni")
        assert response.status_code == 200
        assert "https://api.openai.com" in response.text
        assert "gpt-4o" in response.text
        assert "sk-test-key" not in response.text
        # Should show "active config" badge
        assert "Configurazione attiva" in response.text

    async def test_post_impostazioni_reuses_api_key_when_blank(self, authenticated_client, monkeypatch):
        call_count = 0

        async def mock_test_connectivity(self, base_url, api_key, model_id):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                # Second call should use the stored api_key from first call
                assert api_key == "sk-original-key"
            return None

        monkeypatch.setattr(
            "easyorario.services.llm.LLMService.test_connectivity",
            mock_test_connectivity,
        )

        csrf = _get_csrf_token(authenticated_client)
        # First: set a config
        await authenticated_client.post(
            "/impostazioni",
            data={"base_url": "https://api.openai.com", "api_key": "sk-original-key", "model_id": "gpt-4o"},
            headers={"x-csrftoken": csrf},
        )
        # Second: update with empty api_key — should reuse stored key
        response = await authenticated_client.post(
            "/impostazioni",
            data={"base_url": "https://api.openai.com", "api_key": "", "model_id": "gpt-4o-mini"},
            headers={"x-csrftoken": csrf},
        )
        assert response.status_code == 200
        assert "successo" in response.text.lower()

    async def test_post_impostazioni_with_timeout_shows_error(self, authenticated_client, monkeypatch):
        from easyorario.exceptions import LLMConfigError

        async def mock_test_connectivity(self, base_url, api_key, model_id):
            raise LLMConfigError("llm_timeout")

        monkeypatch.setattr(
            "easyorario.services.llm.LLMService.test_connectivity",
            mock_test_connectivity,
        )

        csrf = _get_csrf_token(authenticated_client)
        response = await authenticated_client.post(
            "/impostazioni",
            data={"base_url": "https://slow.example.com", "api_key": "sk-test", "model_id": "gpt-4o"},
            headers={"x-csrftoken": csrf},
        )
        assert response.status_code == 200
        assert "Timeout" in response.text

    async def test_post_impostazioni_preserves_values_on_error(self, authenticated_client, monkeypatch):
        from easyorario.exceptions import LLMConfigError

        async def mock_test_connectivity(self, base_url, api_key, model_id):
            raise LLMConfigError("llm_connection_failed")

        monkeypatch.setattr(
            "easyorario.services.llm.LLMService.test_connectivity",
            mock_test_connectivity,
        )

        csrf = _get_csrf_token(authenticated_client)
        response = await authenticated_client.post(
            "/impostazioni",
            data={"base_url": "https://bad.example.com", "api_key": "sk-test", "model_id": "my-model"},
            headers={"x-csrftoken": csrf},
        )
        assert response.status_code == 200
        # Form should re-render with submitted base_url and model_id (but NOT api_key)
        assert "https://bad.example.com" in response.text
        assert "my-model" in response.text
        assert "sk-test" not in response.text
