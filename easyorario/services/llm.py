"""LLM service — sole contact point for all external LLM API communication."""

import json
from typing import Any

import httpx
from litestar import Request
from pydantic import BaseModel, ConfigDict, ValidationError

from easyorario.exceptions import LLMConfigError, LLMTranslationError


class ConstraintTranslation(BaseModel):
    """Formal representation of a translated scheduling constraint."""

    model_config = ConfigDict(extra="forbid")

    constraint_type: str
    description: str
    teacher: str | None
    subject: str | None
    days: list[str] | None
    time_slots: list[int] | None
    max_consecutive_hours: int | None
    room: str | None
    notes: str | None


CONSTRAINT_RESPONSE_FORMAT: dict = {
    "type": "json_schema",
    "json_schema": {
        "name": "constraint_translation",
        "strict": True,
        "schema": ConstraintTranslation.model_json_schema(),
    },
}

TRANSLATION_SYSTEM_PROMPT = """\
Sei un traduttore di vincoli per orari scolastici italiani. \
Dato un vincolo espresso in linguaggio naturale italiano, \
traducilo in una rappresentazione strutturata JSON.

Contesto dell'orario:
- Classe: {class_identifier}
- Ore settimanali: {weekly_hours}
- Materie: {subjects}
- Docenti: {teachers}
- Giorni: lunedì, martedì, mercoledì, giovedì, venerdì, sabato
- Fasce orarie: da 1 a {max_slots} (1 = prima ora, 2 = seconda ora, ecc.)

Tipi di vincolo (constraint_type):
- teacher_unavailable: un docente non è disponibile in certi giorni/ore
- teacher_preferred: un docente preferisce certi giorni/ore
- subject_scheduling: una materia deve/non deve essere in certi giorni/ore
- max_consecutive: limite massimo di ore consecutive per materia/docente
- room_requirement: una materia richiede una specifica aula/laboratorio
- general: vincolo che non rientra nelle categorie precedenti

Regole:
- Il campo "description" deve essere una riformulazione chiara e precisa del vincolo in italiano
- Compila solo i campi pertinenti al tipo di vincolo, usa null per gli altri
- I nomi dei giorni devono essere in italiano minuscolo
- Le fasce orarie sono numeri interi (1 = prima ora, 2 = seconda ora, ecc.)
- I nomi di docenti e materie devono corrispondere esattamente a quelli forniti nel contesto, se possibile\
"""


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

    async def translate_constraint(
        self,
        *,
        base_url: str,
        api_key: str,
        model_id: str,
        constraint_text: str,
        timetable_context: dict,
    ) -> dict:
        """Translate an Italian NL constraint to formal representation via LLM."""
        system_prompt = TRANSLATION_SYSTEM_PROMPT.format(**timetable_context)
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f'Traduci questo vincolo: "{constraint_text}"'},
            ],
            "response_format": CONSTRAINT_RESPONSE_FORMAT,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
            except httpx.TimeoutException:
                raise LLMTranslationError("llm_translation_timeout") from None
            except httpx.RequestError:
                raise LLMTranslationError("llm_translation_failed") from None

        if response.status_code in (401, 403):
            raise LLMConfigError("llm_auth_failed")
        if response.status_code >= 400:
            raise LLMTranslationError("llm_translation_failed")

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            result = ConstraintTranslation.model_validate_json(content)
            return result.model_dump()
        except KeyError, IndexError, json.JSONDecodeError, ValidationError:
            raise LLMTranslationError("llm_translation_malformed") from None


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
