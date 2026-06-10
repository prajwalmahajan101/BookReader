"""Typed exception hierarchy for BookReader.

All exceptions raised by the application inherit from :class:`BookReaderError`.
UI code catches this base and routes via a central handler; never blanket-catch
``Exception``. Each subclass attaches context (file path, identifier) so the
error surface in logs is self-describing.
"""

from __future__ import annotations

from pathlib import Path


class BookReaderError(Exception):
    """Base for every BookReader-raised exception."""


class EpubParseError(BookReaderError):
    """Raised when an EPUB file cannot be opened or parsed.

    Attributes:
        path: The EPUB file that failed to parse.
        reason: Short human-readable reason.
    """

    def __init__(self, path: Path, reason: str) -> None:
        """Initialize with offending path and reason."""
        self.path = path
        self.reason = reason
        super().__init__(f"failed to parse EPUB at {path}: {reason}")


class ChapterRenderError(BookReaderError):
    """Raised when chapter XHTML cannot be rendered to terminal output.

    Attributes:
        chapter_id: The chapter identifier from the spine.
        reason: Short human-readable reason.
    """

    def __init__(self, chapter_id: str, reason: str) -> None:
        """Initialize with chapter id and reason."""
        self.chapter_id = chapter_id
        self.reason = reason
        super().__init__(f"failed to render chapter {chapter_id!r}: {reason}")


class PositionStoreError(BookReaderError):
    """Raised when the position-persistence file cannot be read or written.

    Attributes:
        path: The state file involved.
        reason: Short human-readable reason.
    """

    def __init__(self, path: Path, reason: str) -> None:
        """Initialize with state-file path and reason."""
        self.path = path
        self.reason = reason
        super().__init__(f"position store error at {path}: {reason}")


class RepositoryError(BookReaderError):
    """Raised when a library SQLite operation fails.

    Wraps :class:`sqlite3.Error` at the service boundary so UI code can
    catch :class:`BookReaderError` and route through the central handler
    without leaking the underlying driver exception.

    Attributes:
        entity: Short label for what was being acted on (e.g. ``"book"``,
            ``"bookmark"``, ``"position"``).
        reason: Short human-readable reason.
    """

    def __init__(self, entity: str, reason: str) -> None:
        """Initialize with entity label and reason."""
        self.entity = entity
        self.reason = reason
        super().__init__(f"library {entity} error: {reason}")
