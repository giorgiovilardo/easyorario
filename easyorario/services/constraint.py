"""Constraint service for business logic."""

import uuid
from dataclasses import dataclass

import structlog
from litestar.exceptions import NotAuthorizedException

from easyorario.exceptions import InvalidConstraintDataError, LLMConfigError, LLMTranslationError
from easyorario.i18n.errors import MESSAGES
from easyorario.models.constraint import Constraint
from easyorario.models.timetable import Timetable
from easyorario.repositories.constraint import ConstraintRepository
from easyorario.services.llm import LLMService

_log = structlog.get_logger()


@dataclass
class ConflictWarning:
    """A detected pre-solve conflict between constraints."""

    conflict_type: str  # "teacher_double_booking" or "hour_total_mismatch"
    message: str  # Italian human-readable description
    constraint_descriptions: list[str]  # descriptions of the conflicting constraints


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

    async def verify_constraint(
        self,
        *,
        constraint_id: uuid.UUID,
        timetable_id: uuid.UUID,
    ) -> Constraint:
        """Approve a translated constraint."""
        constraint = await self.constraint_repo.get(constraint_id)
        if constraint.timetable_id != timetable_id:
            raise NotAuthorizedException(detail="Insufficient permissions")
        if constraint.status != "translated":
            raise InvalidConstraintDataError("constraint_not_translatable")
        constraint.status = "verified"
        await _log.ainfo("constraint_verified", constraint_id=str(constraint_id))
        return await self.constraint_repo.update(constraint)

    async def reject_constraint(
        self,
        *,
        constraint_id: uuid.UUID,
        timetable_id: uuid.UUID,
    ) -> Constraint:
        """Reject a translated constraint."""
        constraint = await self.constraint_repo.get(constraint_id)
        if constraint.timetable_id != timetable_id:
            raise NotAuthorizedException(detail="Insufficient permissions")
        if constraint.status != "translated":
            raise InvalidConstraintDataError("constraint_not_translatable")
        constraint.status = "rejected"
        constraint.formal_representation = None
        await _log.ainfo("constraint_rejected", constraint_id=str(constraint_id))
        return await self.constraint_repo.update(constraint)

    def detect_conflicts(
        self,
        constraints: list[Constraint],
        timetable: Timetable,
    ) -> list[ConflictWarning]:
        """Detect obvious conflicts among verified constraints before solving."""
        verified = [c for c in constraints if c.status == "verified" and c.formal_representation]
        if not verified:
            return []

        warnings: list[ConflictWarning] = []
        warnings.extend(self._detect_teacher_double_bookings(verified))
        warnings.extend(self._detect_hour_total_mismatches(verified, timetable))
        return warnings

    def _detect_teacher_double_bookings(
        self,
        verified: list[Constraint],
    ) -> list[ConflictWarning]:
        """Find verified constraints that double-book a teacher on the same day+slot."""
        warnings: list[ConflictWarning] = []

        # Group constraints by teacher
        teacher_constraints: dict[str, list[Constraint]] = {}
        for c in verified:
            fr = c.formal_representation
            if not fr or not isinstance(fr, dict):
                _log.warning(
                    "skipping_malformed_formal_representation", constraint_id=str(c.id)
                )  # sync: no await in sync method
                continue
            teacher = fr.get("teacher")
            if not teacher:
                continue
            teacher_constraints.setdefault(teacher, []).append(c)

        # For each teacher with multiple constraints, check for day+slot overlaps
        for teacher, constraints in teacher_constraints.items():
            if len(constraints) < 2:
                continue
            slot_map: dict[tuple[str, int], Constraint] = {}
            # Track already-reported pairs to avoid duplicate warnings
            reported_pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()
            for c in constraints:
                fr = c.formal_representation
                if not fr:
                    continue
                days = fr.get("days") or []
                slots = fr.get("time_slots") or []
                if not days or not slots:
                    continue
                for day in days:
                    for slot in slots:
                        if (day, slot) in slot_map:
                            other = slot_map[(day, slot)]
                            pair_key = (min(c.id, other.id), max(c.id, other.id))
                            if pair_key in reported_pairs:
                                continue
                            reported_pairs.add(pair_key)
                            other_fr = other.formal_representation or {}
                            msg = MESSAGES["conflict_teacher_double_booking"].format(
                                teacher=teacher,
                                day=day,
                                slot=slot,
                            )
                            other_desc = other_fr.get("description", "")
                            c_desc = fr.get("description", "")
                            warnings.append(
                                ConflictWarning(
                                    conflict_type="teacher_double_booking",
                                    message=msg,
                                    constraint_descriptions=[d for d in (other_desc, c_desc) if d],
                                )
                            )
                        else:
                            slot_map[(day, slot)] = c
        return warnings

    def _detect_hour_total_mismatches(
        self,
        verified: list[Constraint],
        timetable: Timetable,
    ) -> list[ConflictWarning]:
        """Check if total subject hours in constraints exceed timetable weekly_hours."""
        warnings: list[ConflictWarning] = []

        total_allocated_slots = 0
        slot_constraints: list[str] = []
        for c in verified:
            fr = c.formal_representation
            if not fr or not isinstance(fr, dict):
                continue
            # Only count constraints that allocate teaching hours
            if fr.get("constraint_type") != "subject_scheduling":
                continue
            days = fr.get("days") or []
            slots = fr.get("time_slots") or []
            if days and slots:
                allocated = len(days) * len(slots)
                total_allocated_slots += allocated
                desc = fr.get("description", "")
                if desc:
                    slot_constraints.append(desc)

        if total_allocated_slots > timetable.weekly_hours:
            msg = MESSAGES["conflict_hour_total_mismatch"].format(
                total=total_allocated_slots,
                weekly_hours=timetable.weekly_hours,
            )
            warnings.append(
                ConflictWarning(
                    conflict_type="hour_total_mismatch",
                    message=msg,
                    constraint_descriptions=slot_constraints,
                )
            )

        return warnings

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
