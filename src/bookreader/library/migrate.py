"""One-shot migrator for Phase-1 positions.json → SQLite.

Phase 1 wrote a small JSON file at ``<state_dir>/positions.json``. Phase 2
moves that data into the ``positions`` table of the library DB. We do this
exactly once: on success the JSON is renamed to
``positions.json.migrated`` so a second startup ignores it.

Migration only writes positions for books that already exist in the
library; orphan entries are logged and left in the file. This keeps the
migration cheap (no EPUB parsing) — the user picks up the position the
next time they open the book through the library.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from bookreader.core.logging import get_logger
from bookreader.core.paths import positions_file

if TYPE_CHECKING:
    from bookreader.library.service import LibraryService

log = get_logger(__name__)


def migrate_positions_json(
    service: LibraryService,
    *,
    source: Path | None = None,
) -> int:
    """Copy positions from a Phase-1 JSON file into the library DB.

    Args:
        service: The library service to write through.
        source: Override path to the JSON file (defaults to
            :func:`bookreader.core.paths.positions_file`). Useful for tests.

    Returns:
        The number of positions actually written. ``0`` if the source is
        missing, empty, or already migrated.
    """
    src = source or positions_file()
    if not src.exists():
        return 0

    try:
        raw = src.read_text(encoding="utf-8")
    except OSError as exc:
        log.warning("could not read positions.json: %s", exc)
        return 0

    if not raw.strip():
        return 0

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("positions.json is malformed: %s", exc)
        return 0

    if not isinstance(data, dict):
        log.warning("positions.json root must be an object")
        return 0

    written = 0
    skipped: list[str] = []
    for identifier, entry in data.items():
        if not isinstance(entry, dict):
            continue
        book = service.find_book_by_identifier(identifier)
        if book is None:
            skipped.append(identifier)
            continue
        try:
            service.save_position(
                book_id=book.id,
                chapter_index=int(entry.get("chapter_index", 0)),
                scroll_offset=int(entry.get("scroll_offset", 0)),
                page_index=(
                    int(entry["page_index"]) if entry.get("page_index") is not None else None
                ),
            )
            written += 1
        except (KeyError, TypeError, ValueError) as exc:
            log.warning("skipping malformed entry %s: %s", identifier, exc)

    if skipped:
        log.info("migrate: %d orphan entries (no matching book)", len(skipped))

    if written:
        target = src.with_suffix(src.suffix + ".migrated")
        try:
            src.rename(target)
            log.info("migrate: wrote %d positions, renamed %s → %s", written, src, target)
        except OSError as exc:
            log.warning("could not rename %s: %s", src, exc)

    return written
