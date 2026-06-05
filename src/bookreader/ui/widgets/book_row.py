"""Cell formatters for the library table.

Kept as plain functions so they're trivially testable and the library
screen can pass the results directly into Textual's :class:`DataTable`.
Per tui-design: never signal with colour alone — every status pairs a
glyph with a colour, and ratings render as `★★★☆☆ (3)` so the number is
readable even in monochrome.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text

if TYPE_CHECKING:
    from bookreader.library.models import Book


_STATUS_FINISHED = ("✓", "green", "finished")
_STATUS_READING = ("●", "blue", "reading")
_STATUS_QUEUED = ("○", "dim", "queued")
_STATUS_PHANTOM = ("◌", "magenta", "wishlist")


def status_cell(book: Book, reading_ids: set[int] | None = None) -> Text:
    """Return a colourful status cell for *book*.

    Args:
        book: The book row to describe.
        reading_ids: Optional set of book ids in the "Currently Reading"
            collection. If supplied and *book* is in it (and not finished),
            we show the reading glyph; otherwise the queued glyph.

    Returns:
        A short :class:`Text`, two cells wide.
    """
    if book.is_phantom:
        glyph, colour, _label = _STATUS_PHANTOM
    elif book.completed_at:
        glyph, colour, _label = _STATUS_FINISHED
    elif reading_ids and book.id in reading_ids:
        glyph, colour, _label = _STATUS_READING
    else:
        glyph, colour, _label = _STATUS_QUEUED
    return Text(glyph, style=colour)


def rating_cell(book: Book) -> Text:
    """Return `★★★☆☆ (3)` for ratings, or `—` when unrated."""
    if book.rating is None:
        return Text("—", style="dim")
    filled = "★" * book.rating
    empty = "☆" * (5 - book.rating)
    return Text(f"{filled}{empty} ({book.rating})", style="yellow")


def title_cell(book: Book) -> Text:
    """Return the title styled in bold."""
    return Text(book.title, style="bold")


def authors_cell(book: Book) -> Text:
    """Return a comma-joined author list, dim style."""
    if not book.authors:
        return Text("—", style="dim")
    return Text(", ".join(book.authors), style="dim")
