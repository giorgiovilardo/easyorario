"""Tests for TimetableController."""

import pytest

from tests.conftest import _get_csrf_token


@pytest.fixture
def timetable_data() -> dict[str, str]:
    """Valid form data for creating a timetable."""
    return {
        "class_identifier": "3A Liceo Scientifico",
        "school_year": "2026/2027",
        "weekly_hours": "30",
        "subjects": "Matematica\nItaliano\nFisica\nStoria",
        "teachers": "Matematica: Prof. Rossi\nItaliano: Prof. Bianchi",
    }


async def test_get_nuovo_as_responsible_professor_returns_form(authenticated_client) -> None:
    """AC #1: Responsible Professor sees the create timetable form."""
    response = await authenticated_client.get("/orario/nuovo")
    assert response.status_code == 200
    assert "Nuovo Orario" in response.text
    assert '<form method="post"' in response.text


async def test_get_nuovo_as_professor_returns_403(authenticated_professor_client) -> None:
    """AC #4: Professor (not Responsible) gets 403."""
    response = await authenticated_professor_client.get("/orario/nuovo")
    assert response.status_code == 403


async def test_post_nuovo_with_valid_data_creates_timetable_and_redirects(authenticated_client, timetable_data) -> None:
    """AC #2: Valid form data creates timetable and redirects to /orario/{id}/vincoli."""
    # GET the form first (mirrors real user flow; also primes the StaticPool connection)
    await authenticated_client.get("/orario/nuovo")
    csrf_token = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        "/orario/nuovo",
        data=timetable_data,
        headers={"x-csrftoken": csrf_token},
        follow_redirects=False,
    )
    assert response.status_code in (301, 302, 303)
    location = response.headers["location"]
    assert "/orario/" in location
    assert "/vincoli" in location


async def test_post_nuovo_with_empty_class_identifier_shows_error(authenticated_client, timetable_data) -> None:
    """AC #5: Empty class_identifier shows Italian validation error."""
    await authenticated_client.get("/orario/nuovo")
    csrf_token = _get_csrf_token(authenticated_client)
    timetable_data["class_identifier"] = ""
    response = await authenticated_client.post(
        "/orario/nuovo",
        data=timetable_data,
        headers={"x-csrftoken": csrf_token},
    )
    assert response.status_code == 200
    assert "obbligatorio" in response.text


async def test_post_nuovo_with_invalid_weekly_hours_shows_error(authenticated_client, timetable_data) -> None:
    """AC #5: Invalid weekly_hours shows Italian validation error."""
    await authenticated_client.get("/orario/nuovo")
    csrf_token = _get_csrf_token(authenticated_client)
    timetable_data["weekly_hours"] = "0"
    response = await authenticated_client.post(
        "/orario/nuovo",
        data=timetable_data,
        headers={"x-csrftoken": csrf_token},
    )
    assert response.status_code == 200
    assert "ore settimanali" in response.text


async def test_get_vincoli_stub_returns_placeholder(authenticated_client, timetable_data) -> None:
    """Redirect target /orario/{id}/vincoli returns a placeholder page."""
    await authenticated_client.get("/orario/nuovo")
    csrf_token = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        "/orario/nuovo",
        data=timetable_data,
        headers={"x-csrftoken": csrf_token},
        follow_redirects=False,
    )
    location = response.headers["location"]
    response = await authenticated_client.get(location)
    assert response.status_code == 200
    assert "Vincoli" in response.text
