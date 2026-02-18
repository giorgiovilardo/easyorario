"""LLM service — sole contact point for all external LLM API communication."""

from typing import Any

import httpx
from litestar import Request

from easyorario.exceptions import LLMConfigError


class LLMService:
    """Stateless service for LLM endpoint operations."""

    async def test_connectivity(self, base_url: str, api_key: str, model_id: str) -> None:
        """Test LLM endpoint connectivity. Raises LLMConfigError on failure."""
        url = f"{base_url.rstrip('/')}/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, headers=headers)
            except httpx.TimeoutException:
                raise LLMConfigError("llm_timeout") from None
            except httpx.RequestError:
                raise LLMConfigError("llm_connection_failed") from None
        if response.status_code in (401, 403):
            raise LLMConfigError("llm_auth_failed")
        if response.status_code >= 400:
            raise LLMConfigError("llm_connection_failed")


def get_llm_config(session: dict[str, Any]) -> dict[str, str] | None:
    """Extract LLM configuration from session. Returns None if not configured."""
    base_url = session.get("llm_base_url")
    api_key = session.get("llm_api_key")
    model_id = session.get("llm_model_id")
    if not base_url or not api_key:
        return None
    return {"base_url": base_url, "api_key": api_key, "model_id": model_id or ""}


def set_llm_config(request: Request, base_url: str, api_key: str, model_id: str) -> None:
    """Store LLM configuration in session alongside existing auth data."""
    session_data = dict(request.session)
    session_data["llm_base_url"] = base_url
    session_data["llm_api_key"] = api_key
    session_data["llm_model_id"] = model_id
    request.set_session(session_data)
