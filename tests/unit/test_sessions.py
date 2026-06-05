"""Tests for the SessionRepo + service session lifecycle."""

from __future__ import annotations

from pathlib import Path

import pytest

from bookreader.library.database import Database
from bookreader.library.service import LibraryService


@pytest.fixture
def service(tmp_path: Path) -> LibraryService:
    return LibraryService(Database(tmp_path / "lib.db"))


def test_start_then_end_session_records_row(
    service: LibraryService, sample_epub: Path
) -> None:
    book = service.add_book(sample_epub)
    session = service.start_session(book.id)
    assert session.id > 0
    assert session.ended_at is None

    service.end_session(session.id, pages_advanced=3)
    rows = service.sessions.list_for(book.id)
    assert len(rows) == 1
    assert rows[0].ended_at is not None
    assert rows[0].pages_advanced == 3


def test_end_session_is_idempotent(service: LibraryService, sample_epub: Path) -> None:
    book = service.add_book(sample_epub)
    s = service.start_session(book.id)
    service.end_session(s.id)
    first = service.sessions.list_for(book.id)[0]
    service.end_session(s.id, pages_advanced=99)
    second = service.sessions.list_for(book.id)[0]
    assert first.ended_at == second.ended_at
    assert second.pages_advanced == 0  # not bumped on second close


def test_close_orphans_stamps_open_sessions(tmp_path: Path, sample_epub: Path) -> None:
    """Sessions left open by a crash get closed on next service construction."""
    db_path = tmp_path / "lib.db"
    svc1 = LibraryService(Database(db_path))
    book = svc1.add_book(sample_epub)
    svc1.start_session(book.id)  # leave open
    svc1.close()

    svc2 = LibraryService(Database(db_path))
    try:
        rows = svc2.sessions.list_for(book.id)
        assert len(rows) == 1
        assert rows[0].ended_at == rows[0].started_at  # closed at start_at
    finally:
        svc2.close()


def test_minutes_read_zero_when_no_sessions(
    service: LibraryService, sample_epub: Path
) -> None:
    book = service.add_book(sample_epub)
    assert service.minutes_read(book.id) == 0


def test_minutes_read_aggregates_closed_sessions(
    service: LibraryService, sample_epub: Path
) -> None:
    book = service.add_book(sample_epub)
    # Insert closed sessions directly so we don't depend on real wall-clock gaps.
    service._db.conn.execute(
        "INSERT INTO sessions (book_id, started_at, ended_at) VALUES "
        "(?, '2026-06-05T00:00:00', '2026-06-05T00:30:00'), "
        "(?, '2026-06-05T01:00:00', '2026-06-05T01:15:00')",
        (book.id, book.id),
    )
    assert service.minutes_read(book.id) == 45
