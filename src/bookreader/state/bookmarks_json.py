"""JSON fallback for bookmarks (used when no library service is wired).

The reader is occasionally invoked with ``--no-library``; in that mode we
still want to support ``m`` / ``'``. This module mirrors the shape of
:mod:`bookreader.state.positions` — a single JSON object on disk, atomic
write-and-rename, frozen dataclass for the record.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bookreader.core.exceptions import PositionStoreError
from bookreader.core.logging import get_logger
from bookreader.core.paths import state_dir

log = get_logger(__name__)


def bookmarks_file() -> Path:
    """Return the path to the JSON bookmarks file."""
    return state_dir() / "bookmarks.json"


@dataclass(frozen=True, slots=True)
class JsonBookmark:
    """A bookmark in the JSON store.

    Attributes:
        id: Stable id within the file (max + 1 on insert).
        chapter_index: Spine index.
        scroll_offset: Vertical scroll offset in lines (or page index).
        note: Optional user note.
        created_at: ISO-8601 UTC timestamp.
    """

    id: int
    chapter_index: int
    scroll_offset: int
    note: str
    created_at: str


class JsonBookmarkStore:
    """Per-book bookmark list, persisted as JSON.

    On-disk layout::

        {
            "<identifier>": [
                {"id": 1, "chapter_index": 4, "scroll_offset": 12,
                 "note": "…", "created_at": "…"},
                …
            ]
        }
    """

    def __init__(self, path: Path | None = None) -> None:
        """Open the store, creating an empty document on first use."""
        self._path = path or bookmarks_file()
        self._data: dict[str, list[dict[str, Any]]] = self._load()

    def list_for(self, identifier: str) -> list[JsonBookmark]:
        """Return bookmarks for *identifier*, newest first."""
        rows = self._data.get(identifier, [])
        out: list[JsonBookmark] = []
        for raw in rows:
            try:
                out.append(
                    JsonBookmark(
                        id=int(raw["id"]),
                        chapter_index=int(raw["chapter_index"]),
                        scroll_offset=int(raw["scroll_offset"]),
                        note=str(raw.get("note", "")),
                        created_at=str(raw["created_at"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                log.warning("ignoring malformed bookmark for %s", identifier)
        # Newest first; ties broken by id so behaviour stays deterministic
        # even when two bookmarks land in the same wall-clock second.
        out.sort(key=lambda b: (b.created_at, b.id), reverse=True)
        return out

    def add(
        self,
        identifier: str,
        *,
        chapter_index: int,
        scroll_offset: int,
        note: str = "",
    ) -> JsonBookmark:
        """Append a bookmark for *identifier* and persist."""
        existing = self._data.setdefault(identifier, [])
        next_id = max((int(r.get("id", 0)) for r in existing), default=0) + 1
        bookmark = JsonBookmark(
            id=next_id,
            chapter_index=chapter_index,
            scroll_offset=scroll_offset,
            note=note,
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        existing.append(asdict(bookmark))
        self._flush()
        return bookmark

    def delete(self, identifier: str, bookmark_id: int) -> None:
        """Remove a bookmark by id (no-op if missing)."""
        rows = self._data.get(identifier)
        if not rows:
            return
        self._data[identifier] = [r for r in rows if int(r.get("id", -1)) != bookmark_id]
        self._flush()

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        """Read the JSON file; tolerate a missing or empty path."""
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
        """Atomic write-and-rename."""
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
            tmp.replace(self._path)
        except OSError as exc:
            raise PositionStoreError(self._path, f"write: {exc}") from exc
