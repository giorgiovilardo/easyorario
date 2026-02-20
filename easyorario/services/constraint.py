"""Constraint service for business logic."""

import uuid

import structlog

from easyorario.exceptions import InvalidConstraintDataError, LLMConfigError, LLMTranslationError
from easyorario.models.constraint import Constraint
from easyorario.models.timetable import Timetable
from easyorario.repositories.constraint import ConstraintRepository
from easyorario.services.llm import LLMService

_log = structlog.get_logger()


class ConstraintService:
    """Handles constraint creation, validation, and translation orchestration."""

    def __init__(self, constraint_repo: ConstraintRepository, llm_service: LLMService) -> None:
        self.constraint_repo = constraint_repo
        self.llm_service = llm_service

    async def add_constraint(
        self,
        *,
        timetable_id: uuid.UUID,
        natural_language_text: str,
    ) -> Constraint:
        """Validate and create a new pending constraint."""
        text = natural_language_text.strip()
        if not text:
            raise InvalidConstraintDataError("constraint_text_required")
        if len(text) > 1000:
            raise InvalidConstraintDataError("constraint_text_too_long")

        constraint = Constraint(
            timetable_id=timetable_id,
            natural_language_text=text,
        )
        created = await self.constraint_repo.add(constraint)
        await _log.ainfo("constraint_added", constraint_id=str(created.id), timetable_id=str(timetable_id))
        return created

    async def list_constraints(self, *, timetable_id: uuid.UUID) -> list[Constraint]:
        """Return all constraints for a timetable, ordered by created_at."""
        return await self.constraint_repo.get_by_timetable(timetable_id)

    async def translate_pending_constraints(
        self,
        *,
        timetable: Timetable,
        llm_config: dict[str, str],
    ) -> list[Constraint]:
        """Translate all pending constraints for a timetable via LLM."""
        constraints = await self.constraint_repo.get_by_timetable(timetable.id)
        pending = [c for c in constraints if c.status in ("pending", "translation_failed")]

        timetable_context = {
            "class_identifier": timetable.class_identifier,
            "weekly_hours": timetable.weekly_hours,
            "subjects": ", ".join(timetable.subjects),
            "teachers": ", ".join(f"{subj}: {teacher}" for subj, teacher in timetable.teachers.items()),
            "max_slots": min(timetable.weekly_hours // 5, 8),
        }

        for i, constraint in enumerate(pending):
            try:
                result = await self.llm_service.translate_constraint(
                    base_url=llm_config["base_url"],
                    api_key=llm_config["api_key"],
                    model_id=llm_config["model_id"],
                    constraint_text=constraint.natural_language_text,
                    timetable_context=timetable_context,
                )
                constraint.formal_representation = result
                constraint.status = "translated"
            except LLMConfigError as exc:
                # Config error (bad API key, etc.) — fail fast, mark all remaining as failed
                await _log.awarning(
                    "constraint_translation_config_error",
                    constraint_id=str(constraint.id),
                    error_key=exc.error_key,
                )
                for remaining in pending[i:]:
                    remaining.status = "translation_failed"
                    remaining.formal_representation = None
                    await self.constraint_repo.update(remaining)
                break
            except LLMTranslationError as exc:
                constraint.status = "translation_failed"
                constraint.formal_representation = None
                await _log.awarning(
                    "constraint_translation_failed",
                    constraint_id=str(constraint.id),
                    error_key=exc.error_key,
                )
            await self.constraint_repo.update(constraint)

        return await self.constraint_repo.get_by_timetable(timetable.id)
