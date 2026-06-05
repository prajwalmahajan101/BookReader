"""Top-level Textual application.

Owns theme state, mounts the reader screen, and routes BookReader exceptions
to a notification widget so a bad book never crashes the app.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import App

from bookreader.core.config import Settings, Theme, load_settings
from bookreader.core.exceptions import BookReaderError
from bookreader.core.logging import get_logger
from bookreader.epub.chapter import Book
from bookreader.state.positions import PositionStore
from bookreader.ui.screens.reader import ReaderScreen

if TYPE_CHECKING:
    pass

log = get_logger(__name__)

_THEME_ORDER: tuple[Theme, ...] = ("dark", "light", "sepia")


class BookReaderApp(App[None]):
    """The Textual app. One book per session in Phase 1."""

    CSS_PATH: ClassVar[str | None] = "styles.tcss"

    def __init__(
        self,
        book: Book,
        *,
        positions: PositionStore | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize with the opened book and (optional) overrides."""
        super().__init__()
        self._book = book
        self._positions = positions or PositionStore()
        self._settings = settings or load_settings()
        self._theme: Theme = self._settings.theme

    def on_mount(self) -> None:
        """Apply the initial theme and push the reader screen."""
        self._apply_theme(self._theme)
        self.push_screen(ReaderScreen(self._book, self._positions))

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
