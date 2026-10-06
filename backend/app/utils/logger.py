"""
Centralized logger configuration.

Every module gets its logger via `get_logger(__name__)` rather than
calling logging.getLogger directly, so log format stays consistent
and we have one place to change it (e.g. to JSON logs in production).
"""
import logging
import sys

from app.config import get_settings

settings = get_settings()

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def _configure_root() -> None:
    root = logging.getLogger()
    if root.handlers:
        return  # already configured (avoid duplicate handlers on reload)

    level = logging.DEBUG if settings.environment == "development" else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    root.setLevel(level)
    root.addHandler(handler)


_configure_root()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
