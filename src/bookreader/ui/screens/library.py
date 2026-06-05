"""Library home screen.

Layout (IDE three-panel):

    ┌─ Header (book count · finished count) ───────────┐
    │ ┌──────────┬───────────────────────────────────┐ │
    │ │ Filters  │ Books table                       │ │
    │ │ All  12  │ ✓ Title · Author · ★★★☆☆ (3)      │ │
    │ │ Now   3  │ ● Title · Author · —              │ │
    │ │ Want  4  │ …                                 │ │
    │ │ Done  5  │                                   │ │
    │ │ Recents  │                                   │ │
    │ └──────────┴───────────────────────────────────┘ │
    │ Status: 12 books · 5 finished · filter: All books│
    │ Footer (always-visible key hints)                │
    └──────────────────────────────────────────────────┘

The screen never touches the database directly; it delegates to
:class:`bookreader.library.LibraryService`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import Horizontal
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Static,
)

from bookreader.core.logging import get_logger
from bookreader.ui.widgets.book_row import (
    authors_cell,
    rating_cell,
    status_cell,
    title_cell,
)
from bookreader.ui.widgets.collection_list import CollectionFilter, CollectionList

if TYPE_CHECKING:
    from collections.abc import Iterable

    from textual.app import ComposeResult

    from bookreader.library.models import Book
    from bookreader.library.service import LibraryService

log = get_logger(__name__)


class _AddBookPrompt(ModalScreen[str | None]):
    """Tiny modal that prompts for an EPUB path."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """Build the modal."""
        yield Static("Add a book — path to .epub:", id="add-prompt-label")
        yield Input(placeholder="/home/you/Documents/book.epub", id="add-prompt-input")
        with Horizontal(id="add-prompt-buttons"):
            yield Button("Add", id="add-prompt-ok", variant="primary")
            yield Button("Cancel", id="add-prompt-cancel")

    def on_mount(self) -> None:
        """Focus the input."""
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Submit on Enter inside the input."""
        self.dismiss(event.value.strip() or None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dispatch button clicks."""
        if event.button.id == "add-prompt-ok":
            self.dismiss(self.query_one(Input).value.strip() or None)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Esc closes the modal."""
        self.dismiss(None)


class _AddWishlistPrompt(ModalScreen[tuple[str, str] | None]):
    """Prompt for a wishlist (file-less) entry: title + author."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """Build the modal."""
        yield Static("Add to wishlist (TBR):", id="wishlist-prompt-label")
        yield Input(placeholder="Title", id="wishlist-title")
        yield Input(placeholder="Author (optional)", id="wishlist-author")
        with Horizontal(id="wishlist-prompt-buttons"):
            yield Button("Add", id="wishlist-ok", variant="primary")
            yield Button("Cancel", id="wishlist-cancel")

    def on_mount(self) -> None:
        """Focus the title field."""
        self.query_one("#wishlist-title", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Tab through fields; submit when on the author input."""
        if event.input.id == "wishlist-title":
            self.query_one("#wishlist-author", Input).focus()
        else:
            self._submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dispatch button clicks."""
        if event.button.id == "wishlist-ok":
            self._submit()
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Esc closes the modal."""
        self.dismiss(None)

    def _submit(self) -> None:
        """Validate and dismiss with ``(title, author)`` or ``None``."""
        title = self.query_one("#wishlist-title", Input).value.strip()
        author = self.query_one("#wishlist-author", Input).value.strip()
        if not title:
            self.notify("Title is required", severity="error", timeout=3)
            self.query_one("#wishlist-title", Input).focus()
            return
        self.dismiss((title, author))


class LibraryScreen(Screen[None]):
    """List of books with a collections sidebar."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("a", "add_book", "Add"),
        Binding("A,shift+a", "add_wishlist", "Wishlist"),
        Binding("d,delete", "remove_book", "Remove"),
        Binding("c", "toggle_complete", "Mark done"),
        Binding("i,enter", "open_book", "Open"),
        Binding("r", "refresh", "Refresh", show=False),
        Binding("1", "rate(1)", "★", show=False),
        Binding("2", "rate(2)", "★★", show=False),
        Binding("3", "rate(3)", "★★★", show=False),
        Binding("4", "rate(4)", "★★★★", show=False),
        Binding("5", "rate(5)", "★★★★★", show=False),
        Binding("0", "rate(0)", "Clear ★", show=False),
        Binding("T,shift+t", "cycle_theme", "Theme"),
        Binding("tab", "focus_next_pane", "Switch", show=False),
        Binding("question_mark,shift+slash", "show_help", "?"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, service: LibraryService) -> None:
        """Initialize with a connected library service."""
        super().__init__()
        self._service = service
        self._books: list[Book] = []
        self._current_filter = CollectionFilter(kind="all", collection_id=None, label="All books")

    def compose(self) -> ComposeResult:
        """Build the widget tree."""
        yield Header(show_clock=False, icon="📚")
        with Horizontal(id="library-content"):
            yield CollectionList(id="library-sidebar")
            yield DataTable(id="library-table", cursor_type="row", zebra_stripes=True)
        yield Static("", id="library-status")
        yield Footer()

    def on_mount(self) -> None:
        """Configure table columns and load the first slice."""
        self.title = "Library"
        table = self.query_one("#library-table", DataTable)
        table.add_columns("·", "Title", "Author", "Rating")
        self._reload()

    # ----- reload ----------------------------------------------------------

    def _reload(self) -> None:
        """Refresh sidebar counts and the visible book list from disk."""
        self._refresh_sidebar()
        self._reload_table()
        self._refresh_status()

    def _refresh_sidebar(self) -> None:
        """Recompute counts and repopulate the sidebar."""
        collections = self._service.list_collections()
        all_books = self._service.list_books()
        recent = self._service.list_recent(limit=10)
        per_collection = {c.id: len(self._service.list_books_in(c.id)) for c in collections}
        sidebar = self.query_one(CollectionList)
        sidebar.set_state(
            collections=collections,
            total_books=len(all_books),
            recent_count=len(recent),
            per_collection=per_collection,
        )

    def _reload_table(self) -> None:
        """Repopulate the table for ``self._current_filter``."""
        if self._current_filter.kind == "all":
            books: list[Book] = self._service.list_books()
        elif self._current_filter.kind == "recents":
            books = self._service.list_recent(limit=50)
        else:
            assert self._current_filter.collection_id is not None
            books = self._service.list_books_in(self._current_filter.collection_id)
        self._books = books

        reading_ids = self._reading_set()
        table = self.query_one("#library-table", DataTable)
        table.clear()
        for book in books:
            table.add_row(
                status_cell(book, reading_ids=reading_ids),
                title_cell(book),
                authors_cell(book),
                rating_cell(book),
                key=str(book.id),
            )

    def _refresh_status(self) -> None:
        """Update the bottom status line."""
        all_books = self._service.list_books()
        total = len(all_books)
        finished = sum(1 for b in all_books if b.completed_at)
        wishlist = sum(1 for b in all_books if b.is_phantom)
        wish_part = f" · {wishlist} wishlist" if wishlist else ""
        self.query_one("#library-status", Static).update(
            f"{total} books · {finished} finished{wish_part}"
            f" · filter: {self._current_filter.label}"
        )

    def _reading_set(self) -> set[int]:
        """Return ids of books in the seeded ``Currently Reading`` collection."""
        col = next(
            (c for c in self._service.list_collections() if c.name == "Currently Reading"),
            None,
        )
        if col is None:
            return set()
        return {b.id for b in self._service.list_books_in(col.id)}

    # ----- selection helpers ----------------------------------------------

    def _selected_book(self) -> Book | None:
        """Return the book under the table cursor, if any."""
        table = self.query_one("#library-table", DataTable)
        if not self._books or table.cursor_row < 0:
            return None
        row = table.cursor_row
        if row >= len(self._books):
            return None
        return self._books[row]

    # ----- messages -------------------------------------------------------

    def on_collection_list_selected(self, message: CollectionList.Selected) -> None:
        """Switch the table to the chosen filter."""
        self._current_filter = message.choice
        self._reload_table()
        self._refresh_status()
        self.query_one("#library-table", DataTable).focus()

    # ----- actions --------------------------------------------------------

    def action_open_book(self) -> None:
        """Open the highlighted book in the reader.

        Phantom (wishlist) rows can't be opened — they have no file. We
        re-route to the attach prompt so the user can supply one.
        """
        book = self._selected_book()
        if book is None:
            return
        if book.is_phantom:
            self.notify(
                "no file attached — press Enter again on the path prompt",
                title="Wishlist entry",
                timeout=3,
            )
            self._prompt_attach(book)
            return
        self.app.action_open_book(book)  # type: ignore[attr-defined]

    def _prompt_attach(self, book: Book) -> None:
        """Open the path prompt to attach an EPUB to a phantom row."""

        def _after(path: str | None) -> None:
            if not path:
                return
            try:
                from pathlib import Path

                self._service.attach_epub(book.id, Path(path).expanduser())
            except Exception as exc:  # central handler shows the error
                self.notify(str(exc), title="Attach failed", severity="error", timeout=6)
                return
            self.notify(f"Attached: {book.title}", timeout=3)
            self._reload()

        self.app.push_screen(_AddBookPrompt(), _after)

    def action_add_book(self) -> None:
        """Prompt for a path and add the book."""

        def _after(path: str | None) -> None:
            if not path:
                return
            try:
                from pathlib import Path

                self._service.add_book(Path(path).expanduser())
            except Exception as exc:  # central handler shows the error
                self.notify(str(exc), title="Add failed", severity="error", timeout=6)
                return
            self._reload()

        self.app.push_screen(_AddBookPrompt(), _after)

    def action_add_wishlist(self) -> None:
        """Prompt for title + author and add a phantom row."""

        def _after(values: tuple[str, str] | None) -> None:
            if not values:
                return
            title, author = values
            authors = (author,) if author else ()
            try:
                self._service.add_wishlist(title=title, authors=authors)
            except Exception as exc:
                self.notify(
                    str(exc), title="Wishlist failed", severity="error", timeout=6
                )
                return
            self.notify(f"Added: {title}", timeout=3)
            self._reload()

        self.app.push_screen(_AddWishlistPrompt(), _after)

    def action_remove_book(self) -> None:
        """Remove the highlighted book."""
        book = self._selected_book()
        if book is None:
            return
        self._service.remove_book(book.id)
        self.notify(f"Removed “{book.title}”", timeout=3)
        self._reload()

    def action_toggle_complete(self) -> None:
        """Flip the completion stamp on the highlighted book."""
        book = self._selected_book()
        if book is None:
            return
        if book.completed_at:
            self._service.mark_incomplete(book.id)
        else:
            self._service.mark_complete(book.id)
        self._reload()

    def action_rate(self, stars: int) -> None:
        """Set the highlighted book's rating (``0`` clears)."""
        book = self._selected_book()
        if book is None:
            return
        self._service.rate(book.id, stars if stars else None)
        self._reload_table()

    def action_refresh(self) -> None:
        """Force a full reload."""
        self._reload()

    def action_cycle_theme(self) -> None:
        """Cycle dark → light → sepia → dark."""
        self.app.action_cycle_theme()  # type: ignore[attr-defined]

    def action_focus_next_pane(self) -> None:
        """Tab between the sidebar and the table."""
        sidebar = self.query_one(CollectionList)
        if sidebar.has_focus:
            self.query_one("#library-table", DataTable).focus()
        else:
            sidebar.focus()

    def action_show_help(self) -> None:
        """Show the most useful keys as a notification."""
        self.notify(
            "Enter open · a add · A wishlist · d remove · c done · 1-5 rate · q quit",
            title="Keys",
            timeout=6,
        )

    def action_quit(self) -> None:
        """Quit the app."""
        self.app.exit()

    # ----- public hooks ---------------------------------------------------

    def reload(self) -> None:
        """Force a reload — used by the app after the reader screen pops."""
        self._reload()

    def collections(self) -> list:
        """Expose the latest collection list (for the detail screen)."""
        return self._service.list_collections()

    def books(self) -> Iterable[Book]:
        """Iterate the currently-visible book slice."""
        return self._books
