"""SQLAlchemy declarative base."""

from advanced_alchemy.base import CommonTableAttributes
from sqlalchemy.orm import DeclarativeBase


class Base(CommonTableAttributes, DeclarativeBase):
    """Base class for all ORM models."""
