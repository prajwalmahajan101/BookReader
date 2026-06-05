"""Reader screen — TOC sidebar plus a scrollable chapter pane.

Layout (IDE three-panel pattern):

    ┌──────────┬─────────────────────────────┐
    │  TOC     │  Chapter text               │
    │  (left)  │  (main, scrollable)         │
    └──────────┴─────────────────────────────┘
            Footer (always-visible key hints)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header

from bookreader.core.logging import get_logger
from bookreader.ui.widgets.chapter_view import ChapterView
from bookreader.ui.widgets.toc_tree import TocTree

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from bookreader.epub.chapter import Book
    from bookreader.state.positions import PositionStore

log = get_logger(__name__)


class ReaderScreen(Screen[None]):
    """The single-file reader. Owns navigation and persistence."""

    BINDINGS = [
        Binding("j,down", "scroll_line(+1)", "Down", show=False),
        Binding("k,up", "scroll_line(-1)", "Up", show=False),
        Binding("space,pagedown", "scroll_page(+1)", "Page ↓"),
        Binding("b,pageup", "scroll_page(-1)", "Page ↑"),
        Binding("n", "next_chapter", "Next ch."),
        Binding("p", "prev_chapter", "Prev ch."),
        Binding("t", "toggle_toc", "TOC"),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("G,shift+g", "scroll_end", "Bottom", show=False),
        Binding("T,shift+t", "cycle_theme", "Theme"),
        Binding("question_mark,shift+slash", "show_help", "?"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, book: Book, positions: PositionStore) -> None:
        """Initialize with an opened book and the persistence store."""
        super().__init__()
        self._book = book
        self._positions = positions
        self._chapter_index = 0

    def compose(self) -> ComposeResult:
        """Build the widget tree."""
        yield Header(show_clock=False)
        with Horizontal():
            yield TocTree(self._book.toc, id="toc")
            with VerticalScroll(id="reader"):
                yield ChapterView(id="chapter")
        yield Footer()

    def on_mount(self) -> None:
        """Restore last-read position and paint the first chapter."""
        self.title = self._book.title
        if self._book.authors:
            self.sub_title = ", ".join(self._book.authors)

        saved = self._positions.get(self._book.identifier)
        start_chapter = saved.chapter_index if saved else 0
        start_offset = saved.scroll_offset if saved else 0
        self._chapter_index = max(0, min(start_chapter, len(self._book.chapters) - 1))

        self._paint_current_chapter()
        if start_offset:
            self.call_after_refresh(self._restore_scroll, start_offset)

    def _paint_current_chapter(self) -> None:
        """Render the current chapter into the chapter view."""
        chapter = self._book.chapters[self._chapter_index]
        view = self.query_one("#chapter", ChapterView)
        view.show_chapter(chapter)
        self.sub_title = (
            f"{', '.join(self._book.authors) + ' — ' if self._book.authors else ''}"
            f"{chapter.title}  "
            f"[{self._chapter_index + 1}/{len(self._book.chapters)}]"
        )
        scroller = self.query_one("#reader", VerticalScroll)
        scroller.scroll_home(animate=False)

    def _restore_scroll(self, offset: int) -> None:
        """Apply a previously-saved scroll offset (lines from top)."""
        scroller = self.query_one("#reader", VerticalScroll)
        scroller.scroll_to(y=offset, animate=False)

    # ----- actions ---------------------------------------------------------

    def action_scroll_line(self, delta: int) -> None:
        """Scroll the reader pane by *delta* lines."""
        scroller = self.query_one("#reader", VerticalScroll)
        scroller.scroll_relative(y=delta, animate=False)

    def action_scroll_page(self, direction: int) -> None:
        """Scroll the reader pane by ~90% of its viewport height."""
        scroller = self.query_one("#reader", VerticalScroll)
        page = max(1, int(scroller.size.height * 0.9))
        scroller.scroll_relative(y=direction * page, animate=False)

    def action_scroll_home(self) -> None:
        """Jump to the top of the current chapter."""
        self.query_one("#reader", VerticalScroll).scroll_home(animate=False)

    def action_scroll_end(self) -> None:
        """Jump to the bottom of the current chapter."""
        self.query_one("#reader", VerticalScroll).scroll_end(animate=False)

    def action_next_chapter(self) -> None:
        """Move to the next chapter, if any."""
        self._jump_to(self._chapter_index + 1)

    def action_prev_chapter(self) -> None:
        """Move to the previous chapter, if any."""
        self._jump_to(self._chapter_index - 1)

    def action_toggle_toc(self) -> None:
        """Show or hide the TOC sidebar."""
        toc = self.query_one("#toc", TocTree)
        toc.toggle_class("-hidden")
        if not toc.has_class("-hidden"):
            toc.focus()

    def action_cycle_theme(self) -> None:
        """Cycle dark → light → sepia → dark."""
        self.app.action_cycle_theme()  # type: ignore[attr-defined]

    def action_show_help(self) -> None:
        """Show a help notification listing the most useful keys."""
        self.notify(
            "j/k scroll • space/b page • n/p chapter • t TOC • T theme • q quit",
            title="Keys",
            timeout=6,
        )

    def action_quit(self) -> None:
        """Save position and exit the app."""
        self._save_position()
        self.app.exit()

    # ----- messages --------------------------------------------------------

    def on_toc_tree_selected(self, message: TocTree.Selected) -> None:
        """Jump to the chapter selected from the TOC."""
        self._jump_to(message.chapter_index)
        # Return focus to the reading pane so scrolling works immediately.
        self.query_one("#reader", VerticalScroll).focus()

    # ----- helpers ---------------------------------------------------------

    def _jump_to(self, index: int) -> None:
        """Switch to chapter *index* if it is within bounds."""
        if 0 <= index < len(self._book.chapters) and index != self._chapter_index:
            self._save_position()
            self._chapter_index = index
            self._paint_current_chapter()

    def _save_position(self) -> None:
        """Persist current chapter + scroll offset."""
        try:
            scroller = self.query_one("#reader", VerticalScroll)
            offset = int(scroller.scroll_y)
        except Exception:  # screen torn down; nothing to save
            return
        try:
            self._positions.save(
                identifier=self._book.identifier,
                chapter_index=self._chapter_index,
                scroll_offset=offset,
            )
        except Exception as exc:  # never crash the app on a save failure
            log.warning("position save failed: %s", exc)
