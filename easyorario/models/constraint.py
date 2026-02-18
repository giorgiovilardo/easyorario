"""Constraint ORM model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from easyorario.models.base import Base

if TYPE_CHECKING:
    from easyorario.models.timetable import Timetable


class Constraint(Base):
    """A scheduling constraint expressed in natural language."""

    __tablename__ = "constraints"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    timetable_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    natural_language_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    formal_representation: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    timetable: Mapped[Timetable] = relationship(back_populates="constraints", lazy="selectin")
