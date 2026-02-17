"""User ORM model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from easyorario.models.base import Base

if TYPE_CHECKING:
    from easyorario.models.timetable import Timetable


class User(Base):
    """Registered user with role-based access."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="responsible_professor")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    timetables: Mapped[list[Timetable]] = relationship(back_populates="owner", lazy="selectin")
