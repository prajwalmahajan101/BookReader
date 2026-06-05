"""Logging setup.

A TUI cannot log to stdout — the alternate screen and raw mode would corrupt
the UI. We log to ``<log_dir>/bookreader.log`` instead. Get a module-level
logger with :func:`get_logger` (never call :func:`logging.getLogger` directly
from application code).
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from bookreader.core.paths import log_dir

_CONFIGURED = False


def _configure_once() -> None:
    """Install the rotating file handler exactly once per process."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = RotatingFileHandler(
        log_dir() / "bookreader.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-5s %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger("bookreader")
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger under the ``bookreader`` namespace.

    Args:
        name: Usually ``__name__``. The ``bookreader.`` prefix is added if
            absent so all logs land in the same file handler.

    Returns:
        A configured :class:`logging.Logger`.
    """
    _configure_once()
    if not name.startswith("bookreader"):
        name = f"bookreader.{name}"
    return logging.getLogger(name)
