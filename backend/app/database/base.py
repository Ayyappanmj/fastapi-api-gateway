"""
Declarative base for all ORM models.

Kept in its own module (separate from session.py) so models can import
Base without triggering engine/session creation — avoids circular imports
between models and the session module.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class every SQLAlchemy model inherits from."""
    pass
