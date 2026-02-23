"""Tests for ConstraintController."""

import re
import uuid

import pytest

from tests.conftest import _get_csrf_token


@pytest.fixture
def timetable_data() -> dict[str, str]:
    """Valid form data for creating a timetable."""
    return {
        "class_identifier": "3A Liceo Scientifico",
        "school_year": "2026/2027",
        "weekly_hours": "30",
        "subjects": "Matematica\nItaliano",
        "teachers": "Matematica: Prof. Rossi",
    }


async def _create_timetable(client, timetable_data: dict[str, str]) -> str:
    """Create a timetable and return the vincoli URL."""
    await client.get("/orario/nuovo")
    csrf = _get_csrf_token(client)
    response = await client.post(
        "/orario/nuovo",
        data=timetable_data,
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )
    assert response.status_code in (301, 302, 303)
    return response.headers["location"]


async def test_get_vincoli_renders_form_with_timetable_info(authenticated_client, timetable_data):
    """AC #1: GET /orario/{id}/vincoli renders form with timetable context."""
    vincoli_url = await _create_timetable(authenticated_client, timetable_data)
    response = await authenticated_client.get(vincoli_url)
    assert response.status_code == 200
    assert "Vincoli" in response.text
    assert "3A Liceo Scientifico" in response.text
    assert '<textarea name="text"' in response.text
    assert "Aggiungi vincolo" in response.text


async def test_post_vincoli_adds_constraint_and_redirects(authenticated_client, timetable_data):
    """AC #1: POST adds constraint and redirects back (PRG)."""
    vincoli_url = await _create_timetable(authenticated_client, timetable_data)
    await authenticated_client.get(vincoli_url)
    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        vincoli_url,
        data={"text": "Prof. Rossi non puo insegnare il lunedi mattina"},
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )
    assert response.status_code in (301, 302, 303)

    # Follow redirect and verify constraint appears
    response = await authenticated_client.get(vincoli_url)
    assert "Prof. Rossi non puo insegnare il lunedi mattina" in response.text
    assert "in attesa" in response.text


async def test_post_vincoli_with_empty_text_shows_error(authenticated_client, timetable_data):
    """AC #7: Empty text shows Italian validation error."""
    vincoli_url = await _create_timetable(authenticated_client, timetable_data)
    await authenticated_client.get(vincoli_url)
    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        vincoli_url,
        data={"text": "   "},
        headers={"x-csrftoken": csrf},
    )
    assert response.status_code == 200
    assert "obbligatorio" in response.text


async def test_get_vincoli_as_professor_returns_403(authenticated_professor_client, timetable_data):
    """AC #8: Professor (not Responsible) gets 403."""
    # Professor can't create timetables, so use a non-existent UUID
    response = await authenticated_professor_client.get(f"/orario/{uuid.uuid4()}/vincoli")
    assert response.status_code == 403


async def test_get_vincoli_for_non_owned_timetable_returns_403(authenticated_client, timetable_data):
    """AC #6: Accessing another user's timetable returns 403.

    Create timetable as user A, then logout, register/login as user B (also RP),
    and try to access user A's timetable.
    """
    vincoli_url = await _create_timetable(authenticated_client, timetable_data)

    # Logout user A
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post("/esci", headers={"x-csrftoken": csrf}, follow_redirects=False)

    # Register and login as user B (also RP)
    await authenticated_client.get("/registrati")
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(
        "/registrati",
        data={"email": "other@example.com", "password": "password123", "password_confirm": "password123"},
        headers={"x-csrftoken": csrf},
    )
    await authenticated_client.get("/accedi")
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(
        "/accedi",
        data={"email": "other@example.com", "password": "password123"},
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )

    # Try to access user A's timetable
    response = await authenticated_client.get(vincoli_url)
    assert response.status_code == 403


async def test_get_vincoli_shows_verifica_button_when_pending(authenticated_client, timetable_data):
    """AC #5: 'Verifica vincoli' button appears when pending constraints exist."""
    vincoli_url = await _create_timetable(authenticated_client, timetable_data)
    await authenticated_client.get(vincoli_url)
    csrf = _get_csrf_token(authenticated_client)

    # Add a constraint to make has_pending = true
    await authenticated_client.post(
        vincoli_url,
        data={"text": "Nessuna lezione dopo le 14"},
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )

    response = await authenticated_client.get(vincoli_url)
    assert "Verifica vincoli" in response.text
    assert "/vincoli/verifica" in response.text


async def test_get_vincoli_with_no_constraints_shows_empty_state(authenticated_client, timetable_data):
    """AC #2: Empty constraints list shows appropriate message."""
    vincoli_url = await _create_timetable(authenticated_client, timetable_data)
    response = await authenticated_client.get(vincoli_url)
    assert response.status_code == 200
    assert "Nessun vincolo inserito" in response.text
    assert "Verifica vincoli" not in response.text


async def test_get_vincoli_for_nonexistent_timetable_returns_404(authenticated_client):
    """Nonexistent timetable ID returns 404."""
    response = await authenticated_client.get(f"/orario/{uuid.uuid4()}/vincoli")
    assert response.status_code == 404


# --- Verification route tests (Story 3.2) ---

VALID_TRANSLATION = {
    "constraint_type": "teacher_unavailable",
    "description": "Prof. Rossi non disponibile lunedì ore 1-3",
    "teacher": "Prof. Rossi",
    "subject": None,
    "days": ["lunedì"],
    "time_slots": [1, 2, 3],
    "max_consecutive_hours": None,
    "room": None,
    "notes": None,
}


async def _set_llm_config(client, monkeypatch):
    """Helper: store LLM config in session via /impostazioni POST."""

    async def mock_test(self, base_url, api_key, model_id):
        return None

    monkeypatch.setattr("easyorario.services.llm.LLMService.test_connectivity", mock_test)
    await client.get("/impostazioni")
    csrf = _get_csrf_token(client)
    await client.post(
        "/impostazioni",
        data={"base_url": "https://api.example.com/v1", "api_key": "sk-test", "model_id": "gpt-4o"},
        headers={"x-csrftoken": csrf},
    )


async def _create_timetable_with_constraints(client, timetable_data):
    """Create a timetable and add constraints, return the vincoli URL."""
    vincoli_url = await _create_timetable(client, timetable_data)
    await client.get(vincoli_url)
    csrf = _get_csrf_token(client)
    for text in ["Prof. Rossi non può il lunedì mattina", "Matematica massimo 2 ore consecutive"]:
        await client.post(
            vincoli_url,
            data={"text": text},
            headers={"x-csrftoken": csrf},
            follow_redirects=False,
        )
    return vincoli_url


async def test_post_verifica_translates_and_renders_page(authenticated_client, timetable_data, monkeypatch):
    """AC #1: POST /verifica translates pending constraints and renders verification page."""
    await _set_llm_config(authenticated_client, monkeypatch)
    vincoli_url = await _create_timetable_with_constraints(authenticated_client, timetable_data)

    async def mock_translate(self, **kwargs):
        return VALID_TRANSLATION

    monkeypatch.setattr("easyorario.services.llm.LLMService.translate_constraint", mock_translate)

    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        vincoli_url + "/verifica",
        headers={"x-csrftoken": csrf},
    )
    assert response.status_code == 200
    assert "Prof. Rossi non disponibile" in response.text
    assert "Verifica vincoli" in response.text


async def test_post_verifica_as_professor_returns_403(authenticated_professor_client, timetable_data, monkeypatch):
    """Role guard blocks Professor (not Responsible Professor)."""
    response = await authenticated_professor_client.post(
        f"/orario/{uuid.uuid4()}/vincoli/verifica",
        headers={"x-csrftoken": _get_csrf_token(authenticated_professor_client)},
    )
    assert response.status_code == 403


async def test_post_verifica_without_llm_config_redirects(authenticated_client, timetable_data):
    """AC #6: No LLM config → redirect to /impostazioni."""
    vincoli_url = await _create_timetable_with_constraints(authenticated_client, timetable_data)
    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        vincoli_url + "/verifica",
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )
    assert response.status_code in (301, 302, 303)
    assert "/impostazioni" in response.headers["location"]


async def test_get_verifica_shows_translated_constraints(authenticated_client, timetable_data, monkeypatch):
    """GET /verifica shows already-translated constraints without re-translating."""
    await _set_llm_config(authenticated_client, monkeypatch)
    vincoli_url = await _create_timetable_with_constraints(authenticated_client, timetable_data)

    async def mock_translate(self, **kwargs):
        return VALID_TRANSLATION

    monkeypatch.setattr("easyorario.services.llm.LLMService.translate_constraint", mock_translate)

    # First POST to translate
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(vincoli_url + "/verifica", headers={"x-csrftoken": csrf})

    # Now GET should show translated constraints
    response = await authenticated_client.get(vincoli_url + "/verifica")
    assert response.status_code == 200
    assert "Prof. Rossi non disponibile" in response.text


async def test_post_verifica_for_non_owned_timetable_returns_403(authenticated_client, timetable_data, monkeypatch):
    """Ownership check: another user's timetable returns 403."""
    await _set_llm_config(authenticated_client, monkeypatch)
    vincoli_url = await _create_timetable_with_constraints(authenticated_client, timetable_data)

    # Logout and login as different user
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post("/esci", headers={"x-csrftoken": csrf}, follow_redirects=False)
    await authenticated_client.get("/registrati")
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(
        "/registrati",
        data={"email": "other@example.com", "password": "password123", "password_confirm": "password123"},
        headers={"x-csrftoken": csrf},
    )
    await authenticated_client.get("/accedi")
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(
        "/accedi",
        data={"email": "other@example.com", "password": "password123"},
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )

    # Set LLM config for new user
    await _set_llm_config(authenticated_client, monkeypatch)

    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        vincoli_url + "/verifica",
        headers={"x-csrftoken": csrf},
    )
    assert response.status_code == 403


async def test_post_verifica_with_no_pending_shows_existing(authenticated_client, timetable_data, monkeypatch):
    """AC #7: No pending constraints → page renders with already-translated constraints."""
    await _set_llm_config(authenticated_client, monkeypatch)
    vincoli_url = await _create_timetable_with_constraints(authenticated_client, timetable_data)

    async def mock_translate(self, **kwargs):
        return VALID_TRANSLATION

    monkeypatch.setattr("easyorario.services.llm.LLMService.translate_constraint", mock_translate)

    # Translate once
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(vincoli_url + "/verifica", headers={"x-csrftoken": csrf})

    # POST again — no pending constraints, should show existing
    response = await authenticated_client.post(
        vincoli_url + "/verifica",
        headers={"x-csrftoken": csrf},
    )
    assert response.status_code == 200
    assert "Prof. Rossi non disponibile" in response.text


async def test_post_verifica_shows_translation_counts(authenticated_client, timetable_data, monkeypatch):
    """Page shows translated and failed counts."""
    await _set_llm_config(authenticated_client, monkeypatch)
    vincoli_url = await _create_timetable_with_constraints(authenticated_client, timetable_data)

    async def mock_translate(self, **kwargs):
        return VALID_TRANSLATION

    monkeypatch.setattr("easyorario.services.llm.LLMService.translate_constraint", mock_translate)

    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        vincoli_url + "/verifica",
        headers={"x-csrftoken": csrf},
    )
    assert response.status_code == 200
    assert "2 da verificare" in response.text


async def test_verification_page_shows_constraint_description(authenticated_client, timetable_data, monkeypatch):
    """Card shows formal_representation.description (human-readable interpretation)."""
    await _set_llm_config(authenticated_client, monkeypatch)
    vincoli_url = await _create_timetable_with_constraints(authenticated_client, timetable_data)

    async def mock_translate(self, **kwargs):
        return VALID_TRANSLATION

    monkeypatch.setattr("easyorario.services.llm.LLMService.translate_constraint", mock_translate)

    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(vincoli_url + "/verifica", headers={"x-csrftoken": csrf})
    assert "Prof. Rossi non disponibile lunedì ore 1-3" in response.text


async def test_verification_page_shows_collapsible_json(authenticated_client, timetable_data, monkeypatch):
    """Card has <details> with JSON output."""
    await _set_llm_config(authenticated_client, monkeypatch)
    vincoli_url = await _create_timetable_with_constraints(authenticated_client, timetable_data)

    async def mock_translate(self, **kwargs):
        return VALID_TRANSLATION

    monkeypatch.setattr("easyorario.services.llm.LLMService.translate_constraint", mock_translate)

    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(vincoli_url + "/verifica", headers={"x-csrftoken": csrf})
    assert "<details>" in response.text
    assert "teacher_unavailable" in response.text


async def test_post_verifica_shows_error_badge_on_failure(authenticated_client, timetable_data, monkeypatch):
    """Failed translations show error badge, failed count, and retry button."""
    await _set_llm_config(authenticated_client, monkeypatch)
    vincoli_url = await _create_timetable_with_constraints(authenticated_client, timetable_data)

    from easyorario.exceptions import LLMTranslationError

    async def mock_translate(self, **kwargs):
        raise LLMTranslationError("llm_translation_failed")

    monkeypatch.setattr("easyorario.services.llm.LLMService.translate_constraint", mock_translate)

    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        vincoli_url + "/verifica",
        headers={"x-csrftoken": csrf},
    )
    assert response.status_code == 200
    assert "errore traduzione" in response.text
    assert "2 errori" in response.text
    assert "Riprova" in response.text


async def test_post_verifica_redirect_includes_flash_message(authenticated_client, timetable_data):
    """AC #6: Redirect to /impostazioni includes message query parameter."""
    vincoli_url = await _create_timetable_with_constraints(authenticated_client, timetable_data)
    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        vincoli_url + "/verifica",
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )
    assert response.status_code in (301, 302, 303)
    assert "message=llm_config_required" in response.headers["location"]


async def test_settings_page_shows_flash_message_from_query(authenticated_client, timetable_data):
    """Settings page displays error when message query param is provided."""
    response = await authenticated_client.get("/impostazioni?message=llm_config_required")
    assert response.status_code == 200
    assert "Configura" in response.text


# --- Verification approval/rejection tests (Story 3.3) ---


async def _create_translated_constraint(client, timetable_data, monkeypatch):
    """Helper: create a timetable with one translated constraint, return (vincoli_url, timetable_id)."""
    vincoli_url = await _create_timetable(client, timetable_data)
    timetable_id = vincoli_url.split("/orario/")[1].split("/vincoli")[0]

    await client.get(vincoli_url)
    csrf = _get_csrf_token(client)
    await client.post(
        vincoli_url,
        data={"text": "Prof. Rossi non può il lunedì"},
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )

    async def mock_translate(self, **kwargs):
        return VALID_TRANSLATION

    monkeypatch.setattr("easyorario.services.llm.LLMService.translate_constraint", mock_translate)

    await _set_llm_config(client, monkeypatch)
    csrf = _get_csrf_token(client)
    await client.post(vincoli_url + "/verifica", headers={"x-csrftoken": csrf})

    return vincoli_url, timetable_id


async def test_post_approva_sets_verified_and_redirects(authenticated_client, timetable_data, monkeypatch):
    """AC #2: POST /approva sets constraint status to verified and redirects to /verifica."""
    vincoli_url, timetable_id = await _create_translated_constraint(authenticated_client, timetable_data, monkeypatch)

    # GET verifica to find the constraint ID from the page
    response = await authenticated_client.get(vincoli_url + "/verifica")
    assert "Approva" in response.text

    # Extract constraint ID from the form action
    match = re.search(r"/vincoli/([0-9a-f-]+)/approva", response.text)
    assert match, "Could not find approve form action in page"
    constraint_id = match.group(1)

    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        f"/orario/{timetable_id}/vincoli/{constraint_id}/approva",
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )
    assert response.status_code in (301, 302, 303)
    assert "/verifica" in response.headers["location"]

    # Follow redirect and verify status changed
    response = await authenticated_client.get(vincoli_url + "/verifica")
    assert "verificato" in response.text


async def test_post_rifiuta_sets_rejected_and_redirects(authenticated_client, timetable_data, monkeypatch):
    """AC #3: POST /rifiuta sets constraint status to rejected and redirects to /verifica."""
    vincoli_url, timetable_id = await _create_translated_constraint(authenticated_client, timetable_data, monkeypatch)

    response = await authenticated_client.get(vincoli_url + "/verifica")
    match = re.search(r"/vincoli/([0-9a-f-]+)/rifiuta", response.text)
    assert match, "Could not find reject form action in page"
    constraint_id = match.group(1)

    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        f"/orario/{timetable_id}/vincoli/{constraint_id}/rifiuta",
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )
    assert response.status_code in (301, 302, 303)
    assert "/verifica" in response.headers["location"]

    response = await authenticated_client.get(vincoli_url + "/verifica")
    assert "rifiutato" in response.text


async def test_post_approva_as_professor_returns_403(authenticated_professor_client, timetable_data):
    """AC #5: Professor (not Responsible) cannot approve."""
    response = await authenticated_professor_client.post(
        f"/orario/{uuid.uuid4()}/vincoli/{uuid.uuid4()}/approva",
        headers={"x-csrftoken": _get_csrf_token(authenticated_professor_client)},
    )
    assert response.status_code == 403


async def test_post_rifiuta_as_professor_returns_403(authenticated_professor_client, timetable_data):
    """AC #5: Professor (not Responsible) cannot reject."""
    response = await authenticated_professor_client.post(
        f"/orario/{uuid.uuid4()}/vincoli/{uuid.uuid4()}/rifiuta",
        headers={"x-csrftoken": _get_csrf_token(authenticated_professor_client)},
    )
    assert response.status_code == 403


async def test_post_approva_non_owned_timetable_returns_403(authenticated_client, timetable_data, monkeypatch):
    """AC #6: Cannot approve constraint on another user's timetable."""
    vincoli_url, timetable_id = await _create_translated_constraint(authenticated_client, timetable_data, monkeypatch)

    response = await authenticated_client.get(vincoli_url + "/verifica")
    match = re.search(r"/vincoli/([0-9a-f-]+)/approva", response.text)
    assert match
    constraint_id = match.group(1)

    # Logout and login as different user
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post("/esci", headers={"x-csrftoken": csrf}, follow_redirects=False)
    await authenticated_client.get("/registrati")
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(
        "/registrati",
        data={"email": "other@example.com", "password": "password123", "password_confirm": "password123"},
        headers={"x-csrftoken": csrf},
    )
    await authenticated_client.get("/accedi")
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(
        "/accedi",
        data={"email": "other@example.com", "password": "password123"},
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )

    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        f"/orario/{timetable_id}/vincoli/{constraint_id}/approva",
        headers={"x-csrftoken": csrf},
    )
    assert response.status_code == 403


async def test_post_rifiuta_non_owned_timetable_returns_403(authenticated_client, timetable_data, monkeypatch):
    """AC #6: Cannot reject constraint on another user's timetable."""
    vincoli_url, timetable_id = await _create_translated_constraint(authenticated_client, timetable_data, monkeypatch)

    response = await authenticated_client.get(vincoli_url + "/verifica")
    match = re.search(r"/vincoli/([0-9a-f-]+)/rifiuta", response.text)
    assert match
    constraint_id = match.group(1)

    # Logout and login as different user
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post("/esci", headers={"x-csrftoken": csrf}, follow_redirects=False)
    await authenticated_client.get("/registrati")
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(
        "/registrati",
        data={"email": "other@example.com", "password": "password123", "password_confirm": "password123"},
        headers={"x-csrftoken": csrf},
    )
    await authenticated_client.get("/accedi")
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(
        "/accedi",
        data={"email": "other@example.com", "password": "password123"},
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )

    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        f"/orario/{timetable_id}/vincoli/{constraint_id}/rifiuta",
        headers={"x-csrftoken": csrf},
    )
    assert response.status_code == 403


async def test_post_approva_non_translated_constraint_returns_error(authenticated_client, timetable_data, monkeypatch):
    """AC #7: Approving a non-translated constraint fails gracefully."""
    vincoli_url, timetable_id = await _create_translated_constraint(authenticated_client, timetable_data, monkeypatch)

    # Get constraint ID
    response = await authenticated_client.get(vincoli_url + "/verifica")
    match = re.search(r"/vincoli/([0-9a-f-]+)/approva", response.text)
    assert match
    constraint_id = match.group(1)

    # Approve once (status becomes verified)
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(
        f"/orario/{timetable_id}/vincoli/{constraint_id}/approva",
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )

    # Try to approve again (now status is verified, not translated)
    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        f"/orario/{timetable_id}/vincoli/{constraint_id}/approva",
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )
    # Should redirect back to /verifica (graceful handling of invalid status)
    assert response.status_code in (301, 302, 303)
    assert "/verifica" in response.headers["location"]


async def test_verification_page_shows_approve_reject_buttons(authenticated_client, timetable_data, monkeypatch):
    """AC #1: Translated constraint cards show Approva and Rifiuta buttons."""
    vincoli_url, _ = await _create_translated_constraint(authenticated_client, timetable_data, monkeypatch)

    response = await authenticated_client.get(vincoli_url + "/verifica")
    assert response.status_code == 200
    assert "Approva" in response.text
    assert "Rifiuta" in response.text
    assert "/approva" in response.text
    assert "/rifiuta" in response.text


async def test_verification_page_shows_genera_link_when_all_verified(authenticated_client, timetable_data, monkeypatch):
    """AC #4: 'Genera orario' link appears when all constraints verified, none translated."""
    vincoli_url, timetable_id = await _create_translated_constraint(authenticated_client, timetable_data, monkeypatch)

    # Approve the constraint
    response = await authenticated_client.get(vincoli_url + "/verifica")
    match = re.search(r"/vincoli/([0-9a-f-]+)/approva", response.text)
    assert match
    constraint_id = match.group(1)

    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(
        f"/orario/{timetable_id}/vincoli/{constraint_id}/approva",
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )

    # Check that Genera orario link appears
    response = await authenticated_client.get(vincoli_url + "/verifica")
    assert "Genera orario" in response.text
    assert f"/orario/{timetable_id}/genera" in response.text


async def test_verification_page_hides_genera_link_when_translated_remain(
    authenticated_client, timetable_data, monkeypatch
):
    """AC #4: No 'Genera orario' when translated constraints still exist."""
    vincoli_url, _ = await _create_translated_constraint(authenticated_client, timetable_data, monkeypatch)

    # Page still has translated constraint — no genera link
    response = await authenticated_client.get(vincoli_url + "/verifica")
    assert "Genera orario" not in response.text


# --- Conflict detection display tests (Story 3.4) ---


async def _create_verified_constraint_via_ui(client, timetable_data, monkeypatch):
    """Helper: create a timetable, add a constraint, translate and approve it.
    Returns (vincoli_url, timetable_id).
    """
    vincoli_url, timetable_id = await _create_translated_constraint(client, timetable_data, monkeypatch)

    # Get constraint ID and approve it
    response = await client.get(vincoli_url + "/verifica")
    match = re.search(r"/vincoli/([0-9a-f-]+)/approva", response.text)
    assert match, "Could not find approve form action in page"
    constraint_id = match.group(1)

    csrf = _get_csrf_token(client)
    await client.post(
        f"/orario/{timetable_id}/vincoli/{constraint_id}/approva",
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )
    return vincoli_url, timetable_id


async def test_constraints_page_shows_conflict_warning(authenticated_client, timetable_data, monkeypatch):
    """AC #3: GET /vincoli renders warning alert when conflicts exist among verified constraints."""
    # Create a timetable with a verified constraint
    vincoli_url, timetable_id = await _create_verified_constraint_via_ui(
        authenticated_client, timetable_data, monkeypatch
    )

    # Now add another constraint that conflicts (same teacher, same day+slot)
    # We need to: add constraint, translate it, approve it
    await authenticated_client.get(vincoli_url)
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(
        vincoli_url,
        data={"text": "Prof. Rossi insegna anche fisica il lunedì"},
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )

    # Translate this new constraint
    async def mock_translate(self, **kwargs):
        return VALID_TRANSLATION  # Same teacher, same days/slots → conflict

    monkeypatch.setattr("easyorario.services.llm.LLMService.translate_constraint", mock_translate)
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(vincoli_url + "/verifica", headers={"x-csrftoken": csrf})

    # Approve the second constraint
    response = await authenticated_client.get(vincoli_url + "/verifica")
    matches = re.findall(r"/vincoli/([0-9a-f-]+)/approva", response.text)
    for constraint_id in matches:
        csrf = _get_csrf_token(authenticated_client)
        await authenticated_client.post(
            f"/orario/{timetable_id}/vincoli/{constraint_id}/approva",
            headers={"x-csrftoken": csrf},
            follow_redirects=False,
        )

    # Now GET /vincoli should show conflict warning
    response = await authenticated_client.get(vincoli_url)
    assert response.status_code == 200
    assert "Attenzione" in response.text or "Conflitto" in response.text


async def test_constraints_page_no_warning_when_no_conflicts(authenticated_client, timetable_data, monkeypatch):
    """AC #4: GET /vincoli shows no warning when no conflicts exist."""
    vincoli_url = await _create_timetable(authenticated_client, timetable_data)

    # Add a single constraint (no possible conflict with just one)
    await authenticated_client.get(vincoli_url)
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(
        vincoli_url,
        data={"text": "Matematica massimo 2 ore consecutive"},
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )

    response = await authenticated_client.get(vincoli_url)
    assert response.status_code == 200
    assert "Conflitto" not in response.text
    assert "conflitti rilevati" not in response.text


async def test_verification_page_shows_conflict_warning(authenticated_client, timetable_data, monkeypatch):
    """AC #3: GET /verifica renders warning alert when conflicts exist among verified constraints."""
    vincoli_url, timetable_id = await _create_verified_constraint_via_ui(
        authenticated_client, timetable_data, monkeypatch
    )

    # Add and approve a second conflicting constraint
    await authenticated_client.get(vincoli_url)
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(
        vincoli_url,
        data={"text": "Prof. Rossi insegna anche fisica il lunedì"},
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )

    async def mock_translate(self, **kwargs):
        return VALID_TRANSLATION

    monkeypatch.setattr("easyorario.services.llm.LLMService.translate_constraint", mock_translate)
    csrf = _get_csrf_token(authenticated_client)
    await authenticated_client.post(vincoli_url + "/verifica", headers={"x-csrftoken": csrf})

    # Approve all translated constraints
    response = await authenticated_client.get(vincoli_url + "/verifica")
    matches = re.findall(r"/vincoli/([0-9a-f-]+)/approva", response.text)
    for constraint_id in matches:
        csrf = _get_csrf_token(authenticated_client)
        await authenticated_client.post(
            f"/orario/{timetable_id}/vincoli/{constraint_id}/approva",
            headers={"x-csrftoken": csrf},
            follow_redirects=False,
        )

    # Now GET /verifica should show conflict warning
    response = await authenticated_client.get(vincoli_url + "/verifica")
    assert response.status_code == 200
    assert "Attenzione" in response.text or "Conflitto" in response.text
