"""Bookmark list / jump screen.

Modal-ish screen pushed from the reader on ``'`` (apostrophe). Shows the
saved bookmarks for the current book; Enter dismisses with the chosen
bookmark; ``d`` removes one in place.

The reader supplies an iterable of :class:`BookmarkRow` records — a
unified shape that hides whether they came from SQLite (`Bookmark`) or
the JSON fallback (`JsonBookmark`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from rich.text import Text
from textual.binding import Binding, BindingType
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, OptionList, Static
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from collections.abc import Iterable

    from textual.app import ComposeResult


@dataclass(frozen=True, slots=True)
class BookmarkRow:
    """A bookmark normalised for display.

    Attributes:
        id: Identifier used by the backing store (DB row id or JSON id).
        chapter_title: Pretty chapter title for display.
        chapter_index: Spine index — what the reader jumps to.
        scroll_offset: Scroll offset to restore.
        page_index: Page index (paged mode), or ``None``.
        note: Optional user note.
        created_at: ISO-8601 timestamp.
    """

    id: int
    chapter_title: str
    chapter_index: int
    scroll_offset: int
    page_index: int | None
    note: str
    created_at: str


class BookmarksScreen(ModalScreen[BookmarkRow | None]):
    """List the bookmarks for the current book and jump to one on Enter."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape,q", "cancel", "Close"),
        Binding("d,delete", "delete", "Delete"),
        Binding("enter", "select", "Jump", show=False),
    ]

    def __init__(self, rows: Iterable[BookmarkRow]) -> None:
        """Initialize with the rows to display."""
        super().__init__()
        self._rows = list(rows)
        self._deleted_ids: set[int] = set()

    def compose(self) -> ComposeResult:
        """Build the modal."""
        yield Header(show_clock=False, icon="🔖")
        if self._rows:
            yield OptionList(
                *[Option(self._format(row), id=str(i)) for i, row in enumerate(self._rows)],
                id="bookmarks-list",
            )
        else:
            yield Static("No bookmarks for this book yet.", id="bookmarks-empty")
        yield Footer()

    def on_mount(self) -> None:
        """Set the title."""
        self.title = "Bookmarks"
        if self._rows:
            self.query_one("#bookmarks-list", OptionList).focus()

    @staticmethod
    def _format(row: BookmarkRow) -> Text:
        """Render a single bookmark row."""
        text = Text()
        text.append(row.chapter_title, style="bold")
        if row.note:
            text.append("  ·  ", style="dim")
            text.append(row.note)
        text.append("\n  ")
        text.append(row.created_at, style="dim")
        return text

    def action_select(self) -> None:
        """Dismiss with the highlighted row."""
        row = self._selected()
        self.dismiss(row)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Translate the option event into a dismiss."""
        if event.option.id is None:
            return
        idx = int(event.option.id)
        if 0 <= idx < len(self._rows):
            self.dismiss(self._rows[idx])

    def action_delete(self) -> None:
        """Mark the highlighted bookmark for deletion and remove the row."""
        row = self._selected()
        if row is None:
            return
        self._deleted_ids.add(row.id)
        lst = self.query_one("#bookmarks-list", OptionList)
        if lst.highlighted is not None:
            lst.remove_option_at_index(lst.highlighted)
        self.notify(f"Deleted bookmark #{row.id}", timeout=2)

    def action_cancel(self) -> None:
        """Esc / q dismisses without jumping."""
        self.dismiss(None)

    @property
    def deleted_ids(self) -> set[int]:
        """Ids the user removed during this session — for the caller to flush."""
        return self._deleted_ids

    def _selected(self) -> BookmarkRow | None:
        try:
            lst = self.query_one("#bookmarks-list", OptionList)
        except Exception:
            return None
        if lst.highlighted is None:
            return None
        if 0 <= lst.highlighted < len(self._rows):
            return self._rows[lst.highlighted]
        return None
