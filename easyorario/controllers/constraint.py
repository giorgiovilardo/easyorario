"""Constraint controller — add, list, and verify scheduling constraints."""

import uuid
from dataclasses import dataclass
from typing import Annotated

from litestar import Controller, Request, get, post
from litestar.enums import RequestEncodingType
from litestar.exceptions import NotAuthorizedException
from litestar.params import Body
from litestar.response import Redirect, Template

from easyorario.exceptions import InvalidConstraintDataError
from easyorario.guards.auth import requires_responsible_professor
from easyorario.i18n.errors import MESSAGES
from easyorario.repositories.timetable import TimetableRepository
from easyorario.services.constraint import ConstraintService
from easyorario.services.llm import get_llm_config


@dataclass
class ConstraintFormData:
    text: str = ""


class ConstraintController(Controller):
    """Constraint input, listing, and verification for a timetable."""

    path = "/orario/{timetable_id:uuid}/vincoli"

    @get("/", guards=[requires_responsible_professor])
    async def list_constraints(
        self,
        request: Request,
        timetable_id: uuid.UUID,
        timetable_repo: TimetableRepository,
        constraint_service: ConstraintService,
    ) -> Template:
        """Render constraint input page with existing constraints."""
        timetable = await timetable_repo.get(timetable_id)
        if timetable.owner_id != request.user.id:
            raise NotAuthorizedException(detail="Insufficient permissions")
        constraints = await constraint_service.list_constraints(timetable_id=timetable_id)
        has_pending = any(c.status == "pending" for c in constraints)
        has_failed = any(c.status == "translation_failed" for c in constraints)
        return Template(
            template_name="pages/timetable_constraints.html",
            context={
                "timetable": timetable,
                "constraints": constraints,
                "has_pending": has_pending,
                "has_failed": has_failed,
                "user": request.user,
            },
        )

    @post("/", guards=[requires_responsible_professor])
    async def add_constraint(
        self,
        request: Request,
        timetable_id: uuid.UUID,
        data: Annotated[ConstraintFormData, Body(media_type=RequestEncodingType.URL_ENCODED)],
        timetable_repo: TimetableRepository,
        constraint_service: ConstraintService,
    ) -> Template | Redirect:
        """Add a new constraint and redirect back to the list (PRG)."""
        timetable = await timetable_repo.get(timetable_id)
        if timetable.owner_id != request.user.id:
            raise NotAuthorizedException(detail="Insufficient permissions")
        try:
            await constraint_service.add_constraint(
                timetable_id=timetable_id,
                natural_language_text=data.text,
            )
            return Redirect(path=f"/orario/{timetable_id}/vincoli")
        except InvalidConstraintDataError as exc:
            constraints = await constraint_service.list_constraints(timetable_id=timetable_id)
            has_pending = any(c.status == "pending" for c in constraints)
            has_failed = any(c.status == "translation_failed" for c in constraints)
            return Template(
                "pages/timetable_constraints.html",
                context={
                    "error": MESSAGES[exc.error_key],
                    "timetable": timetable,
                    "constraints": constraints,
                    "has_pending": has_pending,
                    "has_failed": has_failed,
                    "user": request.user,
                },
            )

    @post("/verifica", guards=[requires_responsible_professor])
    async def translate_constraints(
        self,
        request: Request,
        timetable_id: uuid.UUID,
        timetable_repo: TimetableRepository,
        constraint_service: ConstraintService,
    ) -> Template | Redirect:
        """Trigger LLM translation of pending constraints and render verification page."""
        timetable = await timetable_repo.get(timetable_id)
        if timetable.owner_id != request.user.id:
            raise NotAuthorizedException(detail="Insufficient permissions")

        llm_config = get_llm_config(request.session)
        if not llm_config:
            return Redirect(path="/impostazioni?message=llm_config_required")

        constraints = await constraint_service.translate_pending_constraints(
            timetable=timetable,
            llm_config=llm_config,
        )

        translated_count = sum(1 for c in constraints if c.status == "translated")
        failed_count = sum(1 for c in constraints if c.status == "translation_failed")

        return Template(
            template_name="pages/timetable_verification.html",
            context={
                "timetable": timetable,
                "constraints": constraints,
                "translated_count": translated_count,
                "failed_count": failed_count,
                "user": request.user,
            },
        )

    @get("/verifica", guards=[requires_responsible_professor])
    async def show_verification(
        self,
        request: Request,
        timetable_id: uuid.UUID,
        timetable_repo: TimetableRepository,
        constraint_service: ConstraintService,
    ) -> Template:
        """Show already-translated constraints without re-translating."""
        timetable = await timetable_repo.get(timetable_id)
        if timetable.owner_id != request.user.id:
            raise NotAuthorizedException(detail="Insufficient permissions")

        constraints = await constraint_service.list_constraints(timetable_id=timetable_id)
        translated_count = sum(1 for c in constraints if c.status == "translated")
        failed_count = sum(1 for c in constraints if c.status == "translation_failed")

        return Template(
            template_name="pages/timetable_verification.html",
            context={
                "timetable": timetable,
                "constraints": constraints,
                "translated_count": translated_count,
                "failed_count": failed_count,
                "user": request.user,
            },
        )
