"""Top-level Textual application.

Two entry modes:

- ``bookreader path.epub`` — launches the reader directly. A library
  service is still attached so the book gets added on first open and
  ``last_opened_at`` gets bumped.
- ``bookreader`` (no arg) — launches the library screen. Selecting a row
  pushes the reader; quitting the reader pops back to the library.

Themes live in Textual's first-class theme system
(:meth:`App.register_theme`) so the command palette, header, footer,
notifications, and scrollbars all adapt automatically.

Owns BookReader's exception routing — bad-book errors surface as
notifications, never crash the app.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import App
from textual.theme import Theme

from bookreader.core.config import Settings, ThemeName, load_settings
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


# Theme names are kept short in :class:`Settings` and prefixed for Textual.
_THEME_PREFIX = "bookreader-"
_THEME_ORDER: tuple[ThemeName, ...] = ("dark", "light", "sepia")


def _build_themes() -> list[Theme]:
    """Return the three custom themes registered with the app.

    Each theme supplies the minimum semantic slots Textual needs:

    - ``primary`` and ``accent`` drive focus borders, key hints, palette
      selection.
    - ``foreground`` / ``background`` set body text and screen background.
    - ``surface`` / ``panel`` / ``boost`` colour the chrome (header bar,
      sidebars, status strip).
    """
    return [
        Theme(
            name=f"{_THEME_PREFIX}dark",
            primary="#89b4fa",
            accent="#94e2d5",
            foreground="#cdd6f4",
            background="#1e1e2e",
            surface="#1e1e2e",
            panel="#181825",
            boost="#313244",
            warning="#f9e2af",
            error="#f38ba8",
            success="#a6e3a1",
            dark=True,
        ),
        Theme(
            name=f"{_THEME_PREFIX}light",
            primary="#2563eb",
            accent="#0ea5e9",
            foreground="#1f2328",
            background="#fbf9f1",
            surface="#fbf9f1",
            panel="#f3efe1",
            boost="#e7e1ce",
            warning="#b45309",
            error="#b91c1c",
            success="#15803d",
            dark=False,
        ),
        Theme(
            name=f"{_THEME_PREFIX}sepia",
            primary="#8a4b08",
            accent="#9a5a12",
            foreground="#3b2a14",
            background="#f1e3c2",
            surface="#f1e3c2",
            panel="#e8d5a4",
            boost="#dcc593",
            warning="#92400e",
            error="#9b1c1c",
            success="#3f6212",
            dark=False,
        ),
    ]


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

    def on_mount(self) -> None:
        """Register themes, pick the initial one, push the entry screen."""
        for theme in _build_themes():
            self.register_theme(theme)
        self.theme = _theme_id(self._settings.theme)

        if self._book is not None:
            self.push_screen(self._make_reader(self._book, library_book_id=self._library_book_id))
        elif self._library is not None:
            self.push_screen(LibraryScreen(self._library))
        else:  # bare reader without a book; nothing to show
            self.exit(message="no book and no library — nothing to open")

    # ----- routing actions ------------------------------------------------

    def action_open_book(self, lib_book: LibBook) -> None:
        """Open a book selected from the library screen."""
        if lib_book.file_path is None:
            # Phantom (wishlist) row — no EPUB on disk to open.
            self.notify(
                "This is a wishlist entry; attach an EPUB before opening.",
                title="No file",
                severity="warning",
                timeout=6,
            )
            return
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
        """Cycle through the registered BookReader themes.

        If the active theme isn't one of ours (e.g. the user picked a
        Textual built-in via the command palette), snap back to
        ``bookreader-dark`` so the cycle is predictable. Otherwise step
        to the next BookReader theme in the documented order.
        """
        active = self.theme or ""
        if not active.startswith(_THEME_PREFIX):
            nxt: ThemeName = "dark"
        else:
            current = _theme_short(active)
            idx = _THEME_ORDER.index(current)
            nxt = _THEME_ORDER[(idx + 1) % len(_THEME_ORDER)]
        self.theme = _theme_id(nxt)
        self.notify(f"theme: {nxt}", timeout=2)

    # ----- error routing ---------------------------------------------------

    def _handle_exception(self, error: Exception) -> None:
        """Show BookReader errors as notifications; propagate the rest."""
        if isinstance(error, BookReaderError):
            log.warning("caught %s: %s", type(error).__name__, error)
            self.notify(str(error), title="Error", severity="error", timeout=6)
            return
        super()._handle_exception(error)


def _theme_id(short: ThemeName) -> str:
    """Map a short name (``dark``) to the registered theme id."""
    return f"{_THEME_PREFIX}{short}"


def _theme_short(full: str) -> ThemeName:
    """Strip the ``bookreader-`` prefix back to the short name."""
    if full.startswith(_THEME_PREFIX):
        candidate = full[len(_THEME_PREFIX) :]
        if candidate in _THEME_ORDER:
            return candidate
    return "dark"
