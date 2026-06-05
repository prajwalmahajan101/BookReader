"""Wishlist (TBR) overview screen.

Modal pushed from the library on ``W``. Lists every phantom book
(wishlist entries — title + authors only, no file attached). Enter
dismisses with the highlighted :class:`Book`; ``d`` / ``delete``
marks one for removal in place. The caller flushes deletions on
dismiss.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from rich.text import Text
from textual.binding import Binding, BindingType
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, OptionList, Static
from textual.widgets.option_list import Option

from bookreader.library.models import Book

if TYPE_CHECKING:
    from collections.abc import Iterable

    from textual.app import ComposeResult


class WishlistScreen(ModalScreen[Book | None]):
    """List wishlist books; Enter picks one, ``d`` removes one."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape,q", "cancel", "Close"),
        Binding("d,delete", "delete", "Remove"),
        Binding("enter", "select", "Pick", show=False),
    ]

    def __init__(self, books: Iterable[Book]) -> None:
        """Initialize with the wishlist books to render."""
        super().__init__()
        self._books = [b for b in books]
        self._deleted_ids: set[int] = set()

    def compose(self) -> ComposeResult:
        """Build the modal."""
        yield Header(show_clock=False, icon="⭐")
        if self._books:
            yield OptionList(
                *[
                    Option(self._format(book), id=str(i))
                    for i, book in enumerate(self._books)
                ],
                id="wishlist-list",
            )
        else:
            yield Static(
                "Wishlist is empty — press 'A' on the library to add a TBR entry.",
                id="wishlist-empty",
            )
        yield Footer()

    def on_mount(self) -> None:
        """Set the title and focus the list."""
        self.title = "Wishlist"
        if self._books:
            self.query_one("#wishlist-list", OptionList).focus()

    @staticmethod
    def _format(book: Book) -> Text:
        """Render a single wishlist row: title + authors."""
        text = Text()
        text.append(book.title, style="bold")
        secondary = ", ".join(book.authors) if book.authors else "—"
        text.append("\n  ")
        text.append(secondary, style="dim")
        return text

    def action_select(self) -> None:
        """Dismiss with the highlighted book."""
        self.dismiss(self._selected())

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Translate the option event into a dismiss."""
        if event.option.id is None:
            return
        idx = int(event.option.id)
        if 0 <= idx < len(self._books):
            self.dismiss(self._books[idx])

    def action_delete(self) -> None:
        """Mark the highlighted entry for deletion and remove the row."""
        book = self._selected()
        if book is None:
            return
        self._deleted_ids.add(book.id)
        lst = self.query_one("#wishlist-list", OptionList)
        if lst.highlighted is not None:
            lst.remove_option_at_index(lst.highlighted)
        self.notify(f"Removed “{book.title}” from wishlist", timeout=3)

    def action_cancel(self) -> None:
        """Esc / q dismisses without picking."""
        self.dismiss(None)

    @property
    def deleted_ids(self) -> set[int]:
        """Ids the user removed during this session — caller flushes."""
        return self._deleted_ids

    def _selected(self) -> Book | None:
        try:
            lst = self.query_one("#wishlist-list", OptionList)
        except Exception:
            return None
        if lst.highlighted is None:
            return None
        if 0 <= lst.highlighted < len(self._books):
            return self._books[lst.highlighted]
        return None
