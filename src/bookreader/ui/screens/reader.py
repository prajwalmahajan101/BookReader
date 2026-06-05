"""Reader screen — TOC sidebar plus a scroll- or page-view of the chapter.

Two reading modes:

- ``scroll`` (default): a vertically-scrollable :class:`ChapterView` inside
  a :class:`VerticalScroll`. Line- and page-scroll keys work normally.
- ``paged`` (toggle ``2``): a :class:`PagedView` that lays out the chapter
  as two side-by-side pages, like an open book. ``space`` / ``b`` advance
  one spread; line scroll is disabled.

Layout (IDE three-panel pattern with a constrained reading column):

    ┌────────── Header (book title · author) ──────────┐
    │ ┌──────┬─────────────────────────────────────┐   │
    │ │ TOC  │   Reading column (≤ 84, centered)   │   │
    │ │      │                                     │   │
    │ │ ▶ Ch3│   …prose…   │  …prose…              │   │
    │ │   Ch4│                                     │   │
    │ └──────┴─────────────────────────────────────┘   │
    │ Status:  Chapter · 3/24 · ▰▰▰▱▱▱  37%            │
    │ Footer (always-visible key hints)                │
    └──────────────────────────────────────────────────┘
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Literal

from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Input, Static

from bookreader.core.logging import get_logger
from bookreader.state.bookmarks_json import JsonBookmarkStore
from bookreader.ui.screens.bookmarks import BookmarkRow, BookmarksScreen
from bookreader.ui.widgets.chapter_view import ChapterView
from bookreader.ui.widgets.paged_view import PagedView
from bookreader.ui.widgets.status_bar import StatusBar
from bookreader.ui.widgets.toc_tree import TocTree

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from bookreader.epub.chapter import Book
    from bookreader.library.service import LibraryService
    from bookreader.state.positions import PositionStore


class _BookmarkNotePrompt(ModalScreen[str | None]):
    """One-line prompt for the optional bookmark note."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """Build the modal."""
        yield Static("Bookmark — note (optional):", id="bookmark-prompt-label")
        yield Input(placeholder="e.g. 'great quote'", id="bookmark-prompt-input")
        with Horizontal(id="bookmark-prompt-buttons"):
            yield Button("Save", id="bookmark-ok", variant="primary")
            yield Button("Cancel", id="bookmark-cancel")

    def on_mount(self) -> None:
        """Focus the input."""
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Save on Enter."""
        self.dismiss(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dispatch button clicks."""
        if event.button.id == "bookmark-ok":
            self.dismiss(self.query_one(Input).value)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Esc closes."""
        self.dismiss(None)

log = get_logger(__name__)

Mode = Literal["scroll", "paged"]


class ReaderScreen(Screen[None]):
    """The single-file reader. Owns navigation, mode, and persistence."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("j,down", "scroll_line(+1)", "Down", show=False),
        Binding("k,up", "scroll_line(-1)", "Up", show=False),
        Binding("space,pagedown", "scroll_page(+1)", "Page ↓"),
        Binding("b,pageup", "scroll_page(-1)", "Page ↑"),
        Binding("n", "next_chapter", "Next ch."),
        Binding("p", "prev_chapter", "Prev ch."),
        Binding("t", "toggle_toc", "TOC"),
        Binding("2", "toggle_paged", "2-page"),
        Binding("m", "add_bookmark", "Bookmark"),
        Binding("apostrophe", "list_bookmarks", "Marks"),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("G,shift+g", "scroll_end", "Bottom", show=False),
        Binding("T,shift+t", "cycle_theme", "Theme"),
        Binding("question_mark,shift+slash", "show_help", "?"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        book: Book,
        positions: PositionStore,
        *,
        two_page: bool = False,
        library: LibraryService | None = None,
        library_book_id: int | None = None,
    ) -> None:
        """Initialize.

        Args:
            book: The parsed EPUB.
            positions: Phase-1 JSON position store. Always written.
            two_page: Start in two-page mode.
            library: Optional library service. When set, position saves
                are mirrored to the library DB.
            library_book_id: Row id for *book* in the library, if any.
        """
        super().__init__()
        self._book = book
        self._positions = positions
        self._library = library
        self._library_book_id = library_book_id
        self._chapter_index = 0
        self._mode: Mode = "paged" if two_page else "scroll"
        # JSON-backed bookmark fallback (used when no library is wired)
        self._bookmarks_json = JsonBookmarkStore()
        # Reading-session state (only meaningful when a library is wired)
        self._session_id: int | None = None
        self._session_start_chapter: int = 0

    def compose(self) -> ComposeResult:
        """Build the widget tree."""
        yield Header(show_clock=False, icon="📖")
        with Horizontal(id="content"):
            yield TocTree(self._book.toc, id="toc")
            with VerticalScroll(id="reader"), Container(id="reading-column"):
                yield ChapterView(id="chapter")
                yield PagedView(id="paged")
        yield StatusBar(id="status")
        yield Footer()

    def on_mount(self) -> None:
        """Restore last-read position and paint the first chapter.

        Lookup order: library DB (if connected) → Phase-1 JSON store.
        """
        self.title = self._book.title
        if self._book.authors:
            self.sub_title = " · ".join(self._book.authors)

        # Give the chapter view the book context so it can resolve images.
        self.query_one("#chapter", ChapterView).attach_book(self._book)

        saved = self._load_saved_position()
        start_chapter = saved.chapter_index if saved else 0
        start_offset = saved.scroll_offset if saved else 0
        start_page = saved.page_index if saved else None
        if start_page is not None:
            self._mode = "paged"

        self._chapter_index = max(0, min(start_chapter, len(self._book.chapters) - 1))
        self._apply_mode_classes()
        self._paint_current_chapter()
        if self._mode == "scroll" and start_offset:
            self.call_after_refresh(self._restore_scroll, start_offset)
        elif self._mode == "paged" and start_page:
            self.call_after_refresh(self._restore_page, start_page)

        # Open a reading session if the library is wired. End on quit.
        if self._library is not None and self._library_book_id is not None:
            try:
                session = self._library.start_session(self._library_book_id)
                self._session_id = session.id
                self._session_start_chapter = self._chapter_index
            except Exception as exc:
                log.warning("session start failed: %s", exc)

    # ----- mode helpers ----------------------------------------------------

    def _apply_mode_classes(self) -> None:
        """Toggle visibility + width classes for the active mode.

        Two-page mode widens the reading column (`-paged`) so the spread
        gets ~140 cells instead of the single-column 84-cell cap.
        """
        paged = self.query_one("#paged", PagedView)
        chapter = self.query_one("#chapter", ChapterView)
        scroller = self.query_one("#reader", VerticalScroll)
        column = self.query_one("#reading-column")
        if self._mode == "paged":
            chapter.add_class("-hidden")
            paged.remove_class("-hidden")
            column.add_class("-paged")
            scroller.can_focus = False
        else:
            paged.add_class("-hidden")
            chapter.remove_class("-hidden")
            column.remove_class("-paged")
            scroller.can_focus = True

    def _paint_current_chapter(self, *, scroll_to_end: bool = False) -> None:
        """Render the current chapter into the active widget.

        Args:
            scroll_to_end: If true, jump to the bottom (scroll mode) or the
                last spread (paged mode). Used when entering a chapter from
                the next one.
        """
        chapter = self._book.chapters[self._chapter_index]
        self.query_one("#chapter", ChapterView).show_chapter(chapter)
        self.query_one("#paged", PagedView).show_chapter(chapter, at_last_page=scroll_to_end)

        self.query_one(TocTree).set_current_chapter(self._chapter_index)

        if self._mode == "scroll":
            scroller = self.query_one("#reader", VerticalScroll)
            if scroll_to_end:
                self.call_after_refresh(scroller.scroll_end, animate=False)
            else:
                scroller.scroll_home(animate=False)
        self.call_after_refresh(self._refresh_status)

    def _restore_scroll(self, offset: int) -> None:
        """Apply a previously-saved scroll offset (lines from top)."""
        scroller = self.query_one("#reader", VerticalScroll)
        scroller.scroll_to(y=offset, animate=False)
        self._refresh_status()

    def _restore_page(self, page_index: int) -> None:
        """Apply a previously-saved page index."""
        self.query_one("#paged", PagedView).set_page_index(page_index)
        self._refresh_status()

    def _refresh_status(self) -> None:
        """Recompute the progress display from the current scroll/page state."""
        total = len(self._book.chapters)
        chapter = self._book.chapters[self._chapter_index]
        if self._mode == "paged":
            paged = self.query_one("#paged", PagedView)
            chapter_progress = paged.progress()
        else:
            scroller = self.query_one("#reader", VerticalScroll)
            chapter_progress = (
                scroller.scroll_y / scroller.max_scroll_y if scroller.max_scroll_y else 1.0
            )
        overall = (self._chapter_index + chapter_progress) / total
        self.query_one(StatusBar).set_state(
            chapter_title=chapter.title,
            chapter_index=self._chapter_index,
            chapter_count=total,
            progress=overall,
        )

    # ----- actions ---------------------------------------------------------

    def action_scroll_line(self, delta: int) -> None:
        """Scroll one line in scroll mode; ignored in paged mode."""
        if self._mode == "paged":
            return
        if self._at_boundary(delta) and self._flow_to_adjacent_chapter(delta):
            return
        self.query_one("#reader", VerticalScroll).scroll_relative(y=delta, animate=False)
        self._refresh_status()

    def action_scroll_page(self, direction: int) -> None:
        """Advance one page (or spread); flow into the adjacent chapter at the edge.

        Args:
            direction: ``+1`` for Space/PageDown, ``-1`` for ``b``/PageUp.
        """
        if self._mode == "paged":
            paged = self.query_one("#paged", PagedView)
            moved = paged.next_spread() if direction > 0 else paged.prev_spread()
            if not moved:
                self._flow_to_adjacent_chapter(direction)
            self._refresh_status()
            return

        if self._at_boundary(direction) and self._flow_to_adjacent_chapter(direction):
            return
        scroller = self.query_one("#reader", VerticalScroll)
        page = max(1, int(scroller.size.height * 0.9))
        scroller.scroll_relative(y=direction * page, animate=False)
        self._refresh_status()

    def action_scroll_home(self) -> None:
        """Jump to the start of the current chapter."""
        if self._mode == "paged":
            self.query_one("#paged", PagedView).set_page_index(0)
        else:
            self.query_one("#reader", VerticalScroll).scroll_home(animate=False)
        self._refresh_status()

    def action_scroll_end(self) -> None:
        """Jump to the end of the current chapter."""
        if self._mode == "paged":
            paged = self.query_one("#paged", PagedView)
            paged.set_page_index(max(0, paged.total_pages() - 2))
        else:
            self.query_one("#reader", VerticalScroll).scroll_end(animate=False)
        self._refresh_status()

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

    def action_toggle_paged(self) -> None:
        """Toggle between scroll and two-page reading modes."""
        self._save_position()
        self._mode = "paged" if self._mode == "scroll" else "scroll"
        self._apply_mode_classes()
        # Force the paged view to re-paginate against the new visible size.
        if self._mode == "paged":
            self.query_one("#paged", PagedView).refresh(layout=True)
        self.call_after_refresh(self._refresh_status)
        self.notify(f"mode: {self._mode}", timeout=2)

    def action_cycle_theme(self) -> None:
        """Cycle dark → light → sepia → dark."""
        self.app.action_cycle_theme()  # type: ignore[attr-defined]

    def action_add_bookmark(self) -> None:
        """Prompt for an optional note, then save a bookmark at the cursor."""
        chapter_idx = self._chapter_index
        scroll_offset = self._current_offset()

        def _after(note: str | None) -> None:
            if note is None:
                return
            note = note.strip()
            self._save_bookmark(
                chapter_index=chapter_idx,
                scroll_offset=scroll_offset,
                note=note,
            )
            self.notify("Bookmarked", timeout=2)

        self.app.push_screen(_BookmarkNotePrompt(), _after)

    def action_list_bookmarks(self) -> None:
        """Show the list of bookmarks for this book; jump on Enter."""
        rows = self._collect_bookmark_rows()
        screen = BookmarksScreen(rows)

        def _after(chosen: BookmarkRow | None) -> None:
            for bid in screen.deleted_ids:
                self._delete_bookmark(bid)
            if chosen is None:
                return
            self._jump_to(chosen.chapter_index)
            if self._mode == "paged" and chosen.page_index is not None:
                self.call_after_refresh(self._restore_page, chosen.page_index)
            elif self._mode == "scroll" and chosen.scroll_offset:
                self.call_after_refresh(self._restore_scroll, chosen.scroll_offset)

        self.app.push_screen(screen, _after)

    def action_show_help(self) -> None:
        """Show a help notification listing the most useful keys."""
        self.notify(
            "j/k scroll · space/b page · n/p chapter · t TOC · m mark · "
            "' marks · 2 spread · q quit",
            title="Keys",
            timeout=6,
        )

    def action_quit(self) -> None:
        """Save position, close the session, and pop back to the previous screen."""
        self._save_position()
        self._end_session()
        if len(self.app.screen_stack) > 1:
            self.app.pop_screen()
            # Tell the library screen to refresh counts / last-opened.
            for screen in self.app.screen_stack:
                if hasattr(screen, "reload"):
                    screen.reload()  # type: ignore[attr-defined]
        else:
            self.app.exit()

    # ----- messages --------------------------------------------------------

    def on_toc_tree_selected(self, message: TocTree.Selected) -> None:
        """Jump to the chapter selected from the TOC."""
        self._jump_to(message.chapter_index)
        # Return focus to the reading pane so scrolling works immediately.
        if self._mode == "scroll":
            self.query_one("#reader", VerticalScroll).focus()

    # ----- helpers ---------------------------------------------------------

    def _jump_to(self, index: int, *, scroll_to_end: bool = False) -> None:
        """Switch to chapter *index* if it is within bounds.

        Args:
            index: Target spine index.
            scroll_to_end: Start at the bottom rather than the top (used
                when entering a chapter from the next one).
        """
        if 0 <= index < len(self._book.chapters) and index != self._chapter_index:
            self._save_position()
            self._chapter_index = index
            self._paint_current_chapter(scroll_to_end=scroll_to_end)

    def _at_boundary(self, direction: int) -> bool:
        """Return ``True`` if a scroll in *direction* has nowhere to go.

        Scroll mode only — paged mode handles boundaries on its own.
        """
        scroller = self.query_one("#reader", VerticalScroll)
        if direction > 0:
            return scroller.scroll_y >= scroller.max_scroll_y
        return scroller.scroll_y <= 0

    def _flow_to_adjacent_chapter(self, direction: int) -> bool:
        """Move into the next/previous chapter at a boundary.

        Args:
            direction: ``+1`` for forward, ``-1`` for backward.

        Returns:
            ``True`` if a chapter switch happened.
        """
        target = self._chapter_index + (1 if direction > 0 else -1)
        if not 0 <= target < len(self._book.chapters):
            return False
        self._jump_to(target, scroll_to_end=direction < 0)
        chapter = self._book.chapters[target]
        self.notify(
            f"{chapter.title}  [{target + 1}/{len(self._book.chapters)}]",
            timeout=2,
        )
        return True

    def _save_position(self) -> None:
        """Persist current chapter + scroll offset (and page if paged).

        Writes to both the Phase-1 JSON store and the library DB (when a
        :class:`LibraryService` is attached). Failures are logged but never
        raised — a crash on save would lose the user's place.
        """
        try:
            if self._mode == "paged":
                page_index: int | None = self.query_one("#paged", PagedView).page_index
                scroll_offset = 0
            else:
                page_index = None
                scroll_offset = int(self.query_one("#reader", VerticalScroll).scroll_y)
        except Exception:  # screen torn down; nothing to save
            return
        try:
            self._positions.save(
                identifier=self._book.identifier,
                chapter_index=self._chapter_index,
                scroll_offset=scroll_offset,
                page_index=page_index,
            )
        except Exception as exc:  # never crash the app on a save failure
            log.warning("position save (json) failed: %s", exc)
        if self._library is not None and self._library_book_id is not None:
            try:
                self._library.save_position(
                    book_id=self._library_book_id,
                    chapter_index=self._chapter_index,
                    scroll_offset=scroll_offset,
                    page_index=page_index,
                )
            except Exception as exc:
                log.warning("position save (library) failed: %s", exc)

    def _load_saved_position(self) -> object | None:
        """Find a saved position; library DB wins over the JSON store."""
        if self._library is not None and self._library_book_id is not None:
            lib_pos = self._library.get_position(self._library_book_id)
            if lib_pos is not None:
                return lib_pos
        return self._positions.get(self._book.identifier)

    # ----- bookmarks -------------------------------------------------------

    def _current_offset(self) -> int:
        """Return the offset to record on a bookmark for the active mode."""
        try:
            if self._mode == "paged":
                return self.query_one("#paged", PagedView).page_index
            return int(self.query_one("#reader", VerticalScroll).scroll_y)
        except Exception:
            return 0

    def _save_bookmark(
        self,
        *,
        chapter_index: int,
        scroll_offset: int,
        note: str,
    ) -> None:
        """Persist a bookmark to the library DB or JSON fallback."""
        if self._library is not None and self._library_book_id is not None:
            try:
                self._library.bookmarks.add(
                    self._library_book_id,
                    chapter_index=chapter_index,
                    scroll_offset=scroll_offset,
                    note=note,
                )
                return
            except Exception as exc:
                log.warning("bookmark save (library) failed: %s", exc)
        try:
            self._bookmarks_json.add(
                self._book.identifier,
                chapter_index=chapter_index,
                scroll_offset=scroll_offset,
                note=note,
            )
        except Exception as exc:
            log.warning("bookmark save (json) failed: %s", exc)

    def _delete_bookmark(self, bookmark_id: int) -> None:
        """Delete a bookmark from whichever store owns it."""
        if self._library is not None and self._library_book_id is not None:
            try:
                self._library.bookmarks.delete(bookmark_id)
                return
            except Exception as exc:
                log.warning("bookmark delete (library) failed: %s", exc)
        try:
            self._bookmarks_json.delete(self._book.identifier, bookmark_id)
        except Exception as exc:
            log.warning("bookmark delete (json) failed: %s", exc)

    def _end_session(self) -> None:
        """Close the reading session if one is open (idempotent)."""
        if self._library is None or self._session_id is None:
            return
        pages = max(0, self._chapter_index - self._session_start_chapter)
        try:
            self._library.end_session(self._session_id, pages_advanced=pages)
        except Exception as exc:
            log.warning("session end failed: %s", exc)
        self._session_id = None

    def _collect_bookmark_rows(self) -> list[BookmarkRow]:
        """Pull bookmarks from the active store and normalise for display."""
        rows: list[BookmarkRow] = []
        chapters = self._book.chapters
        if self._library is not None and self._library_book_id is not None:
            for bm in self._library.bookmarks.list_for(self._library_book_id):
                title = (
                    chapters[bm.chapter_index].title
                    if 0 <= bm.chapter_index < len(chapters)
                    else f"Chapter {bm.chapter_index + 1}"
                )
                rows.append(
                    BookmarkRow(
                        id=bm.id,
                        chapter_title=title,
                        chapter_index=bm.chapter_index,
                        scroll_offset=bm.scroll_offset,
                        page_index=None,
                        note=bm.note,
                        created_at=bm.created_at,
                    )
                )
            return rows
        for bm in self._bookmarks_json.list_for(self._book.identifier):
            title = (
                chapters[bm.chapter_index].title
                if 0 <= bm.chapter_index < len(chapters)
                else f"Chapter {bm.chapter_index + 1}"
            )
            rows.append(
                BookmarkRow(
                    id=bm.id,
                    chapter_title=title,
                    chapter_index=bm.chapter_index,
                    scroll_offset=bm.scroll_offset,
                    page_index=None,
                    note=bm.note,
                    created_at=bm.created_at,
                )
            )
        return rows
