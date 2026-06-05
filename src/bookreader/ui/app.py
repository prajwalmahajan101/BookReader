"""Top-level Textual application.

Two entry modes:

- ``bookreader path.epub`` — launches the reader directly. A library
  service is still attached so the book gets added on first open and
  ``last_opened_at`` gets bumped.
- ``bookreader`` (no arg) — launches the library screen. Selecting a row
  pushes the reader; quitting the reader pops back to the library.

Owns theme state and routes BookReader exceptions to a notification widget
so a bad book never crashes the app.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import App

from bookreader.core.config import Settings, Theme, load_settings
from bookreader.core.exceptions import BookReaderError
from bookreader.core.logging import get_logger
from bookreader.epub.reader import open_book
from bookreader.state.positions import PositionStore
from bookreader.ui.screens.library import LibraryScreen
from bookreader.ui.screens.reader import ReaderScreen

if TYPE_CHECKING:
    from bookreader.epub.chapter import Book as EpubBook
    from bookreader.library.models import Book as LibBook
    from bookreader.library.service import LibraryService

log = get_logger(__name__)

_THEME_ORDER: tuple[Theme, ...] = ("dark", "light", "sepia")


class BookReaderApp(App[None]):
    """The Textual app. Routes between library and reader screens."""

    CSS_PATH: ClassVar[str | None] = "styles.tcss"

    def __init__(
        self,
        *,
        book: EpubBook | None = None,
        positions: PositionStore | None = None,
        settings: Settings | None = None,
        library: LibraryService | None = None,
        library_book_id: int | None = None,
    ) -> None:
        """Initialize.

        Args:
            book: Pre-loaded EPUB to open immediately. If ``None`` the
                library screen is the entry point.
            positions: Phase-1 JSON store. Defaults to the XDG location.
            settings: Runtime config. Defaults to env-loaded.
            library: Optional library service. If supplied, the reader
                screen mirrors position saves through it and the library
                home screen becomes reachable.
            library_book_id: When *book* is supplied alongside a *library*,
                this is the row id used to scope position saves.
        """
        super().__init__()
        self._book = book
        self._positions = positions or PositionStore()
        self._settings = settings or load_settings()
        self._library = library
        self._library_book_id = library_book_id
        self._theme: Theme = self._settings.theme

    def on_mount(self) -> None:
        """Apply the initial theme and push the entry screen."""
        self._apply_theme(self._theme)
        if self._book is not None:
            self.push_screen(self._make_reader(self._book, library_book_id=self._library_book_id))
        elif self._library is not None:
            self.push_screen(LibraryScreen(self._library))
        else:  # bare reader without a book; nothing to show
            self.exit(message="no book and no library — nothing to open")

    # ----- routing actions ------------------------------------------------

    def action_open_book(self, lib_book: LibBook) -> None:
        """Open a book selected from the library screen."""
        try:
            parsed = open_book(lib_book.file_path)
        except BookReaderError as exc:
            self.notify(str(exc), title="Open failed", severity="error", timeout=6)
            return
        if self._library is not None:
            self._library.touch_opened(lib_book.id)
        self.push_screen(self._make_reader(parsed, library_book_id=lib_book.id))

    def _make_reader(
        self,
        parsed: EpubBook,
        *,
        library_book_id: int | None = None,
    ) -> ReaderScreen:
        """Build a :class:`ReaderScreen` wired to the active services."""
        return ReaderScreen(
            parsed,
            positions=self._positions,
            two_page=self._settings.two_page_default,
            library=self._library,
            library_book_id=library_book_id,
        )

    # ----- theme handling --------------------------------------------------

    def action_cycle_theme(self) -> None:
        """Advance to the next theme in :data:`_THEME_ORDER`."""
        idx = _THEME_ORDER.index(self._theme)
        self._apply_theme(_THEME_ORDER[(idx + 1) % len(_THEME_ORDER)])

    def _apply_theme(self, theme: Theme) -> None:
        """Swap theme classes on the root app element."""
        for name in _THEME_ORDER:
            self.remove_class(f"-theme-{name}")
        self.add_class(f"-theme-{theme}")
        self._theme = theme
        self.notify(f"theme: {theme}", timeout=2)

    # ----- error routing ---------------------------------------------------

    def _handle_exception(self, error: Exception) -> None:
        """Show BookReader errors as notifications; propagate the rest."""
        if isinstance(error, BookReaderError):
            log.warning("caught %s: %s", type(error).__name__, error)
            self.notify(str(error), title="Error", severity="error", timeout=6)
            return
        super()._handle_exception(error)
