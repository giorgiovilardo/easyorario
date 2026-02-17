"""Timetable ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from easyorario.models.base import Base
from easyorario.models.user import User


class Timetable(Base):
    """A class timetable owned by a Responsible Professor."""

    __tablename__ = "timetables"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    class_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    school_year: Mapped[str] = mapped_column(String(20), nullable=False)
    weekly_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    subjects: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    teachers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    owner: Mapped[User] = relationship(back_populates="timetables", lazy="selectin")
