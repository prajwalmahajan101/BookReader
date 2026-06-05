"""Tests for ``bookreader.library.migrate``."""

from __future__ import annotations

import json
from pathlib import Path

from bookreader.library.database import Database
from bookreader.library.migrate import migrate_positions_json
from bookreader.library.service import LibraryService


def test_no_file_returns_zero(tmp_path: Path) -> None:
    service = LibraryService(Database(tmp_path / "lib.db"))
    written = migrate_positions_json(service, source=tmp_path / "nope.json")
    assert written == 0


def test_orphan_entries_skipped(tmp_path: Path) -> None:
    service = LibraryService(Database(tmp_path / "lib.db"))
    src = tmp_path / "positions.json"
    src.write_text(
        json.dumps(
            {
                "unknown-id": {
                    "chapter_index": 1,
                    "scroll_offset": 5,
                    "updated_at": "2026-06-05T00:00:00+00:00",
                }
            }
        ),
        encoding="utf-8",
    )
    written = migrate_positions_json(service, source=src)
    assert written == 0
    assert src.exists()  # not renamed when nothing was written


def test_matching_entries_written_and_file_renamed(
    tmp_path: Path, sample_epub: Path
) -> None:
    service = LibraryService(Database(tmp_path / "lib.db"))
    book = service.add_book(sample_epub)

    src = tmp_path / "positions.json"
    src.write_text(
        json.dumps(
            {
                book.identifier: {
                    "chapter_index": 2,
                    "scroll_offset": 200,
                    "page_index": None,
                    "updated_at": "2026-06-05T00:00:00+00:00",
                }
            }
        ),
        encoding="utf-8",
    )

    written = migrate_positions_json(service, source=src)
    assert written == 1
    assert not src.exists()
    assert (tmp_path / "positions.json.migrated").exists()

    pos = service.get_position(book.id)
    assert pos is not None
    assert pos.chapter_index == 2
    assert pos.scroll_offset == 200


def test_malformed_json_logged_and_ignored(tmp_path: Path) -> None:
    service = LibraryService(Database(tmp_path / "lib.db"))
    src = tmp_path / "positions.json"
    src.write_text("not json", encoding="utf-8")
    assert migrate_positions_json(service, source=src) == 0
    assert src.exists()
