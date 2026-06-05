"""Read / write last-read positions per book.

Keyed by EPUB ``dc:identifier`` (or SHA-1 fallback computed at parse time)
so the same book at different paths resumes in the same place. The on-disk
layout is a single JSON object::

    {
        "<identifier>": {
            "chapter_index": 12,
            "scroll_offset": 3400,
            "updated_at": "2026-06-05T10:11:12+00:00"
        },
        ...
    }
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bookreader.core.exceptions import PositionStoreError
from bookreader.core.logging import get_logger
from bookreader.core.paths import positions_file

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Position:
    """A single book's last-read location.

    Attributes:
        chapter_index: Spine index of the current chapter.
        scroll_offset: Vertical scroll in lines from the chapter top.
            Used in scroll mode.
        page_index: Index of the left page of the current spread in
            two-page mode. ``None`` if the book was last read in scroll mode.
        updated_at: ISO-8601 UTC timestamp of the last write.
    """

    chapter_index: int
    scroll_offset: int
    updated_at: str
    page_index: int | None = None


class PositionStore:
    """JSON-backed positions store.

    Loads the entire file on construction (tiny: kilobytes) and writes back
    on every save. Atomic via write-and-rename.
    """

    def __init__(self, path: Path | None = None) -> None:
        """Initialize against *path* (defaults to the XDG state location)."""
        self._path = path or positions_file()
        self._data: dict[str, dict[str, Any]] = self._load()

    def get(self, identifier: str) -> Position | None:
        """Return the saved position for *identifier* if any."""
        raw = self._data.get(identifier)
        if raw is None:
            return None
        try:
            page_raw = raw.get("page_index")
            return Position(
                chapter_index=int(raw["chapter_index"]),
                scroll_offset=int(raw["scroll_offset"]),
                updated_at=str(raw["updated_at"]),
                page_index=int(page_raw) if page_raw is not None else None,
            )
        except (KeyError, TypeError, ValueError):
            log.warning("ignoring malformed position for %s", identifier)
            return None

    def save(
        self,
        identifier: str,
        chapter_index: int,
        scroll_offset: int,
        page_index: int | None = None,
    ) -> Position:
        """Record a new position for *identifier* and flush to disk.

        Args:
            identifier: Book identifier (``dc:identifier`` or SHA-1 fallback).
            chapter_index: Spine index of the current chapter.
            scroll_offset: Vertical scroll offset in lines (scroll mode).
            page_index: Left-page index in a two-page spread, or ``None``
                if the book was last read in scroll mode.

        Returns:
            The :class:`Position` written.

        Raises:
            PositionStoreError: If the file cannot be written.
        """
        position = Position(
            chapter_index=chapter_index,
            scroll_offset=scroll_offset,
            updated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            page_index=page_index,
        )
        self._data[identifier] = asdict(position)
        self._flush()
        return position

    def _load(self) -> dict[str, dict[str, Any]]:
        """Load the JSON file, tolerating a missing or empty path."""
        if not self._path.exists():
            return {}
        try:
            raw = self._path.read_text(encoding="utf-8")
            if not raw.strip():
                return {}
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise PositionStoreError(self._path, f"load: {exc}") from exc
        if not isinstance(data, dict):
            raise PositionStoreError(self._path, "root must be a JSON object")
        return data

    def _flush(self) -> None:
        """Write current state to disk atomically."""
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
            tmp.replace(self._path)
        except OSError as exc:
            raise PositionStoreError(self._path, f"write: {exc}") from exc
