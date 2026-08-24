"""Shared FastAPI dependencies."""

from tracemark.config import Settings, get_settings
from tracemark.db.session import get_session

__all__ = ["Settings", "get_settings", "get_session"]
