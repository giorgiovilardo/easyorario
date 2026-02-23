"""Tests for the ConstraintService."""

import uuid
from unittest.mock import AsyncMock

import pytest
from litestar.exceptions import NotAuthorizedException
from sqlalchemy.ext.asyncio import AsyncSession

from easyorario.exceptions import InvalidConstraintDataError, LLMConfigError, LLMTranslationError
from easyorario.models.constraint import Constraint
from easyorario.models.timetable import Timetable
from easyorario.repositories.constraint import ConstraintRepository
from easyorario.services.constraint import ConstraintService
from easyorario.services.llm import LLMService

VALID_TRANSLATION = {
    "constraint_type": "teacher_unavailable",
    "description": "Prof. Rossi non è disponibile il lunedì nelle ore 1-3",
    "teacher": "Prof. Rossi",
    "subject": None,
    "days": ["lunedì"],
    "time_slots": [1, 2, 3],
    "max_consecutive_hours": None,
    "room": None,
    "notes": None,
}


@pytest.fixture
def llm_service() -> LLMService:
    return LLMService()


@pytest.fixture
async def constraint_service(db_session: AsyncSession, llm_service: LLMService) -> ConstraintService:
    repo = ConstraintRepository(session=db_session)
    return ConstraintService(constraint_repo=repo, llm_service=llm_service)


async def test_add_constraint_with_valid_text_creates_pending(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """Adding a constraint with valid text should create it with status='pending'."""
    constraint = await constraint_service.add_constraint(
        timetable_id=db_timetable.id,
        natural_language_text="Prof. Rossi non puo insegnare il lunedi mattina",
    )

    assert constraint.id is not None
    assert constraint.natural_language_text == "Prof. Rossi non puo insegnare il lunedi mattina"
    assert constraint.status == "pending"
    assert constraint.timetable_id == db_timetable.id


async def test_add_constraint_with_empty_text_raises(db_timetable: Timetable, constraint_service: ConstraintService):
    """Empty or whitespace-only text should raise InvalidConstraintDataError."""
    with pytest.raises(InvalidConstraintDataError) as exc_info:
        await constraint_service.add_constraint(
            timetable_id=db_timetable.id,
            natural_language_text="   ",
        )
    assert exc_info.value.error_key == "constraint_text_required"


async def test_add_constraint_with_text_over_1000_chars_raises(
    db_timetable: Timetable, constraint_service: ConstraintService
):
    """Text exceeding 1000 characters should raise InvalidConstraintDataError."""
    long_text = "a" * 1001
    with pytest.raises(InvalidConstraintDataError) as exc_info:
        await constraint_service.add_constraint(
            timetable_id=db_timetable.id,
            natural_language_text=long_text,
        )
    assert exc_info.value.error_key == "constraint_text_too_long"


async def test_list_constraints_returns_ordered(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """list_constraints should return constraints ordered by created_at ascending."""
    await constraint_service.add_constraint(
        timetable_id=db_timetable.id,
        natural_language_text="Vincolo 1",
    )
    await constraint_service.add_constraint(
        timetable_id=db_timetable.id,
        natural_language_text="Vincolo 2",
    )
    await db_session.flush()

    results = await constraint_service.list_constraints(timetable_id=db_timetable.id)

    assert len(results) == 2
    assert results[0].natural_language_text == "Vincolo 1"
    assert results[1].natural_language_text == "Vincolo 2"


# --- translate_pending_constraints tests ---


async def _add_pending_constraint(db_session: AsyncSession, timetable: Timetable, text: str) -> Constraint:
    """Helper: add a pending constraint directly to the DB."""
    c = Constraint(timetable_id=timetable.id, natural_language_text=text)
    db_session.add(c)
    await db_session.flush()
    return c


def _make_llm_config() -> dict[str, str]:
    return {"base_url": "https://api.example.com/v1", "api_key": "sk-test", "model_id": "gpt-4o"}


async def test_constraint_service_accepts_llm_service_dependency(db_session: AsyncSession):
    """ConstraintService constructor accepts LLMService as a dependency."""
    repo = ConstraintRepository(session=db_session)
    llm = LLMService()
    svc = ConstraintService(constraint_repo=repo, llm_service=llm)
    assert svc.llm_service is llm


async def test_translate_pending_constraints_translates_all_pending(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService, monkeypatch
):
    """All pending constraints should be translated and stored."""
    await _add_pending_constraint(db_session, db_timetable, "Vincolo 1")
    await _add_pending_constraint(db_session, db_timetable, "Vincolo 2")

    mock_translate = AsyncMock(return_value=VALID_TRANSLATION)
    monkeypatch.setattr(constraint_service.llm_service, "translate_constraint", mock_translate)

    results = await constraint_service.translate_pending_constraints(
        timetable=db_timetable, llm_config=_make_llm_config()
    )
    assert mock_translate.call_count == 2
    translated = [c for c in results if c.status == "translated"]
    assert len(translated) == 2
    assert translated[0].formal_representation == VALID_TRANSLATION


async def test_translate_pending_constraints_partial_failure(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService, monkeypatch
):
    """When some translations fail, successful ones still get translated status."""
    await _add_pending_constraint(db_session, db_timetable, "Good constraint")
    await _add_pending_constraint(db_session, db_timetable, "Bad constraint")

    call_count = 0

    async def mock_translate(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise LLMTranslationError("llm_translation_failed")
        return VALID_TRANSLATION

    monkeypatch.setattr(constraint_service.llm_service, "translate_constraint", mock_translate)

    results = await constraint_service.translate_pending_constraints(
        timetable=db_timetable, llm_config=_make_llm_config()
    )
    translated = [c for c in results if c.status == "translated"]
    failed = [c for c in results if c.status == "translation_failed"]
    assert len(translated) == 1
    assert len(failed) == 1
    assert failed[0].formal_representation is None


async def test_translate_pending_constraints_no_pending_returns_existing(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService, monkeypatch
):
    """When there are no pending constraints, LLM is not called and existing constraints are returned."""
    c = await _add_pending_constraint(db_session, db_timetable, "Already done")
    c.status = "translated"
    c.formal_representation = VALID_TRANSLATION
    await db_session.flush()

    mock_translate = AsyncMock(return_value=VALID_TRANSLATION)
    monkeypatch.setattr(constraint_service.llm_service, "translate_constraint", mock_translate)

    results = await constraint_service.translate_pending_constraints(
        timetable=db_timetable, llm_config=_make_llm_config()
    )
    assert mock_translate.call_count == 0
    assert len(results) == 1
    assert results[0].status == "translated"


async def test_translate_pending_constraints_updates_status_to_translated(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService, monkeypatch
):
    """Status changes from 'pending' to 'translated' on success."""
    c = await _add_pending_constraint(db_session, db_timetable, "Test constraint")
    assert c.status == "pending"

    mock_translate = AsyncMock(return_value=VALID_TRANSLATION)
    monkeypatch.setattr(constraint_service.llm_service, "translate_constraint", mock_translate)

    results = await constraint_service.translate_pending_constraints(
        timetable=db_timetable, llm_config=_make_llm_config()
    )
    assert results[0].status == "translated"
    assert results[0].formal_representation == VALID_TRANSLATION


async def test_translate_pending_constraints_updates_status_to_failed(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService, monkeypatch
):
    """Status changes from 'pending' to 'translation_failed' on LLMTranslationError."""
    await _add_pending_constraint(db_session, db_timetable, "Bad constraint")

    mock_translate = AsyncMock(side_effect=LLMTranslationError("llm_translation_failed"))
    monkeypatch.setattr(constraint_service.llm_service, "translate_constraint", mock_translate)

    results = await constraint_service.translate_pending_constraints(
        timetable=db_timetable, llm_config=_make_llm_config()
    )
    assert results[0].status == "translation_failed"
    assert results[0].formal_representation is None


async def test_translate_pending_constraints_skips_non_pending(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService, monkeypatch
):
    """Already translated/verified constraints are not re-translated."""
    c1 = await _add_pending_constraint(db_session, db_timetable, "Already translated")
    c1.status = "translated"
    c1.formal_representation = VALID_TRANSLATION
    await _add_pending_constraint(db_session, db_timetable, "Pending one")
    await db_session.flush()

    mock_translate = AsyncMock(return_value=VALID_TRANSLATION)
    monkeypatch.setattr(constraint_service.llm_service, "translate_constraint", mock_translate)

    results = await constraint_service.translate_pending_constraints(
        timetable=db_timetable, llm_config=_make_llm_config()
    )
    assert mock_translate.call_count == 1  # only the pending one
    assert len(results) == 2


async def test_translate_pending_constraints_builds_timetable_context(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService, monkeypatch
):
    """Timetable context passed to LLMService has correct keys."""
    await _add_pending_constraint(db_session, db_timetable, "Test")

    captured_kwargs: dict = {}

    async def mock_translate(**kwargs):
        captured_kwargs.update(kwargs)
        return VALID_TRANSLATION

    monkeypatch.setattr(constraint_service.llm_service, "translate_constraint", mock_translate)

    await constraint_service.translate_pending_constraints(timetable=db_timetable, llm_config=_make_llm_config())

    ctx = captured_kwargs["timetable_context"]
    assert ctx["class_identifier"] == "3A"
    assert ctx["weekly_hours"] == 30
    assert "Matematica" in ctx["subjects"]
    assert "max_slots" in ctx


async def test_translate_pending_constraints_fails_fast_on_config_error(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService, monkeypatch
):
    """LLMConfigError stops the loop and marks all remaining constraints as failed."""
    await _add_pending_constraint(db_session, db_timetable, "Constraint 1")
    await _add_pending_constraint(db_session, db_timetable, "Constraint 2")
    await _add_pending_constraint(db_session, db_timetable, "Constraint 3")

    mock_translate = AsyncMock(side_effect=LLMConfigError("llm_auth_failed"))
    monkeypatch.setattr(constraint_service.llm_service, "translate_constraint", mock_translate)

    results = await constraint_service.translate_pending_constraints(
        timetable=db_timetable, llm_config=_make_llm_config()
    )
    # Only one API call should have been made (fail-fast)
    assert mock_translate.call_count == 1
    # All three should be marked as failed
    failed = [c for c in results if c.status == "translation_failed"]
    assert len(failed) == 3


async def test_translate_pending_constraints_retries_previously_failed(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService, monkeypatch
):
    """Previously failed constraints are retried on subsequent translate calls."""
    c = await _add_pending_constraint(db_session, db_timetable, "Previously failed")
    c.status = "translation_failed"
    c.formal_representation = None
    await db_session.flush()

    mock_translate = AsyncMock(return_value=VALID_TRANSLATION)
    monkeypatch.setattr(constraint_service.llm_service, "translate_constraint", mock_translate)

    results = await constraint_service.translate_pending_constraints(
        timetable=db_timetable, llm_config=_make_llm_config()
    )
    assert mock_translate.call_count == 1
    assert results[0].status == "translated"
    assert results[0].formal_representation == VALID_TRANSLATION


# --- verify_constraint / reject_constraint tests (Story 3.3) ---


async def _add_translated_constraint(db_session: AsyncSession, timetable: Timetable) -> Constraint:
    """Helper: add a constraint with status 'translated' and valid formal_representation."""
    c = Constraint(
        timetable_id=timetable.id,
        natural_language_text="Prof. Rossi non può il lunedì",
        status="translated",
        formal_representation=VALID_TRANSLATION,
    )
    db_session.add(c)
    await db_session.flush()
    return c


async def test_verify_constraint_sets_status_to_verified(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """Happy path: verify_constraint changes status from translated to verified."""
    c = await _add_translated_constraint(db_session, db_timetable)

    result = await constraint_service.verify_constraint(constraint_id=c.id, timetable_id=db_timetable.id)

    assert result.status == "verified"
    assert result.formal_representation == VALID_TRANSLATION


async def test_reject_constraint_sets_status_to_rejected(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """Happy path: reject_constraint changes status to rejected and clears formal_representation."""
    c = await _add_translated_constraint(db_session, db_timetable)

    result = await constraint_service.reject_constraint(constraint_id=c.id, timetable_id=db_timetable.id)

    assert result.status == "rejected"
    assert result.formal_representation is None


async def test_verify_constraint_non_translated_raises(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """Status guard: only 'translated' constraints can be verified."""
    for status in ("pending", "translation_failed", "verified", "rejected"):
        c = Constraint(
            timetable_id=db_timetable.id,
            natural_language_text=f"Constraint with status {status}",
            status=status,
        )
        db_session.add(c)
        await db_session.flush()

        with pytest.raises(InvalidConstraintDataError) as exc_info:
            await constraint_service.verify_constraint(constraint_id=c.id, timetable_id=db_timetable.id)
        assert exc_info.value.error_key == "constraint_not_translatable"


async def test_reject_constraint_non_translated_raises(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """Status guard: only 'translated' constraints can be rejected."""
    for status in ("pending", "translation_failed", "verified", "rejected"):
        c = Constraint(
            timetable_id=db_timetable.id,
            natural_language_text=f"Constraint with status {status}",
            status=status,
        )
        db_session.add(c)
        await db_session.flush()

        with pytest.raises(InvalidConstraintDataError) as exc_info:
            await constraint_service.reject_constraint(constraint_id=c.id, timetable_id=db_timetable.id)
        assert exc_info.value.error_key == "constraint_not_translatable"


async def test_verify_constraint_wrong_timetable_raises(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """Timetable ownership: constraint must belong to the given timetable."""
    c = await _add_translated_constraint(db_session, db_timetable)

    with pytest.raises(NotAuthorizedException):
        await constraint_service.verify_constraint(constraint_id=c.id, timetable_id=uuid.uuid4())


async def test_reject_constraint_wrong_timetable_raises(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """Timetable ownership: constraint must belong to the given timetable."""
    c = await _add_translated_constraint(db_session, db_timetable)

    with pytest.raises(NotAuthorizedException):
        await constraint_service.reject_constraint(constraint_id=c.id, timetable_id=uuid.uuid4())


# --- detect_conflicts tests (Story 3.4) ---


async def _add_verified_constraint(
    db_session: AsyncSession,
    timetable: Timetable,
    formal_representation: dict,
) -> Constraint:
    """Helper: create a verified constraint with given formal_representation."""
    constraint = Constraint(
        timetable_id=timetable.id,
        natural_language_text="Test constraint",
        formal_representation=formal_representation,
        status="verified",
    )
    db_session.add(constraint)
    await db_session.flush()
    return constraint


async def test_detect_conflicts_finds_teacher_double_booking(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """Two verified constraints with same teacher, same day+slot → conflict warning."""
    await _add_verified_constraint(
        db_session,
        db_timetable,
        {
            "description": "Prof. Rossi insegna matematica lunedì 1-2 ora",
            "teacher": "Prof. Rossi",
            "days": ["lunedì"],
            "time_slots": [1, 2],
        },
    )
    await _add_verified_constraint(
        db_session,
        db_timetable,
        {
            "description": "Prof. Rossi insegna fisica lunedì 2 ora",
            "teacher": "Prof. Rossi",
            "days": ["lunedì"],
            "time_slots": [2],
        },
    )
    constraints = await constraint_service.list_constraints(timetable_id=db_timetable.id)
    warnings = constraint_service.detect_conflicts(constraints, db_timetable)

    assert len(warnings) == 1
    assert warnings[0].conflict_type == "teacher_double_booking"
    assert "Prof. Rossi" in warnings[0].message
    assert len(warnings[0].constraint_descriptions) == 2


async def test_detect_conflicts_finds_hour_total_mismatch(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """Total allocated slots exceed timetable weekly_hours → conflict warning."""
    # db_timetable has weekly_hours=30; create constraints summing to > 30 slots
    for i in range(7):
        await _add_verified_constraint(
            db_session,
            db_timetable,
            {
                "description": f"Subject {i} — 5 days x 1 slot",
                "teacher": f"Prof{i}",
                "days": ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì"],
                "time_slots": [i + 1],
            },
        )
    # 7 constraints * 5 days * 1 slot = 35 > 30
    constraints = await constraint_service.list_constraints(timetable_id=db_timetable.id)
    warnings = constraint_service.detect_conflicts(constraints, db_timetable)

    hour_warnings = [w for w in warnings if w.conflict_type == "hour_total_mismatch"]
    assert len(hour_warnings) == 1
    assert "35" in hour_warnings[0].message
    assert "30" in hour_warnings[0].message


async def test_detect_conflicts_returns_empty_for_no_conflicts(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """Non-overlapping constraints → empty list."""
    await _add_verified_constraint(
        db_session,
        db_timetable,
        {
            "description": "Prof. Rossi lunedì 1 ora",
            "teacher": "Prof. Rossi",
            "days": ["lunedì"],
            "time_slots": [1],
        },
    )
    await _add_verified_constraint(
        db_session,
        db_timetable,
        {
            "description": "Prof. Bianchi lunedì 2 ora",
            "teacher": "Prof. Bianchi",
            "days": ["lunedì"],
            "time_slots": [2],
        },
    )
    constraints = await constraint_service.list_constraints(timetable_id=db_timetable.id)
    warnings = constraint_service.detect_conflicts(constraints, db_timetable)
    assert warnings == []


async def test_detect_conflicts_skips_non_verified_constraints(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """Pending/rejected/translated constraints are ignored."""
    for status in ("pending", "translated", "rejected", "translation_failed"):
        c = Constraint(
            timetable_id=db_timetable.id,
            natural_language_text=f"Constraint with status {status}",
            formal_representation={
                "description": f"Constraint {status}",
                "teacher": "Prof. Rossi",
                "days": ["lunedì"],
                "time_slots": [1],
            },
            status=status,
        )
        db_session.add(c)
    await db_session.flush()

    constraints = await constraint_service.list_constraints(timetable_id=db_timetable.id)
    warnings = constraint_service.detect_conflicts(constraints, db_timetable)
    assert warnings == []


async def test_detect_conflicts_skips_none_formal_representation(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """Constraint with None formal_representation → skipped, no crash."""
    c = Constraint(
        timetable_id=db_timetable.id,
        natural_language_text="Broken constraint",
        formal_representation=None,
        status="verified",
    )
    db_session.add(c)
    await _add_verified_constraint(
        db_session,
        db_timetable,
        {
            "description": "Valid constraint",
            "teacher": "Prof. Rossi",
            "days": ["lunedì"],
            "time_slots": [1],
        },
    )
    await db_session.flush()

    constraints = await constraint_service.list_constraints(timetable_id=db_timetable.id)
    warnings = constraint_service.detect_conflicts(constraints, db_timetable)
    # Should not crash, just skip the broken one
    assert warnings == []


async def test_detect_conflicts_empty_constraints_returns_empty(
    db_timetable: Timetable, constraint_service: ConstraintService
):
    """Empty constraint list → empty warnings."""
    warnings = constraint_service.detect_conflicts([], db_timetable)
    assert warnings == []


async def test_detect_conflicts_no_overlap_different_days(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """Same teacher, different days → no conflict."""
    await _add_verified_constraint(
        db_session,
        db_timetable,
        {
            "description": "Prof. Rossi lunedì 1 ora",
            "teacher": "Prof. Rossi",
            "days": ["lunedì"],
            "time_slots": [1],
        },
    )
    await _add_verified_constraint(
        db_session,
        db_timetable,
        {
            "description": "Prof. Rossi martedì 1 ora",
            "teacher": "Prof. Rossi",
            "days": ["martedì"],
            "time_slots": [1],
        },
    )
    constraints = await constraint_service.list_constraints(timetable_id=db_timetable.id)
    warnings = constraint_service.detect_conflicts(constraints, db_timetable)
    teacher_warnings = [w for w in warnings if w.conflict_type == "teacher_double_booking"]
    assert teacher_warnings == []


async def test_detect_conflicts_no_overlap_different_slots(
    db_session: AsyncSession, db_timetable: Timetable, constraint_service: ConstraintService
):
    """Same teacher, same day, different slots → no conflict."""
    await _add_verified_constraint(
        db_session,
        db_timetable,
        {
            "description": "Prof. Rossi lunedì 1 ora",
            "teacher": "Prof. Rossi",
            "days": ["lunedì"],
            "time_slots": [1],
        },
    )
    await _add_verified_constraint(
        db_session,
        db_timetable,
        {
            "description": "Prof. Rossi lunedì 2 ora",
            "teacher": "Prof. Rossi",
            "days": ["lunedì"],
            "time_slots": [2],
        },
    )
    constraints = await constraint_service.list_constraints(timetable_id=db_timetable.id)
    warnings = constraint_service.detect_conflicts(constraints, db_timetable)
    teacher_warnings = [w for w in warnings if w.conflict_type == "teacher_double_booking"]
    assert teacher_warnings == []
