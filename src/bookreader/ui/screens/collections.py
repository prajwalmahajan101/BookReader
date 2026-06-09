"""Collections overview screen.

Modal pushed from the library on ``C``. Lists every book in the library
grouped by collection. Each book row shows its title (bold) and either
its file path (dim) or ``[wishlist]`` for phantom rows.

Enter dismisses with the highlighted :class:`Book`; the caller decides
whether to open it (skipped for phantom rows).
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class CollectionGroup:
    """A collection plus the books inside it.

    Attributes:
        name: Collection name (display).
        books: Books in the collection, in repo order.
    """

    name: str
    books: tuple[Book, ...]


class CollectionsScreen(ModalScreen[Book | None]):
    """List every book grouped by collection; Enter picks one."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape,q", "cancel", "Close"),
        Binding("enter", "select", "Open", show=False),
    ]

    def __init__(self, groups: Iterable[CollectionGroup]) -> None:
        """Initialize with the collection groups to render."""
        super().__init__()
        self._groups = [g for g in groups]
        self._index: list[Book] = []

    def compose(self) -> ComposeResult:
        """Build the modal."""
        yield Header(show_clock=False, icon="📚")
        if any(g.books for g in self._groups):
            options: list[Option] = []
            for group in self._groups:
                if not group.books:
                    continue
                if options:
                    options.append(Option("", disabled=True))
                options.append(Option(self._header(group), disabled=True))
                for book in group.books:
                    option_id = str(len(self._index))
                    self._index.append(book)
                    options.append(Option(self._format(book), id=option_id))
            yield OptionList(*options, id="collections-list")
        else:
            yield Static("No books yet — press 'a' to add one.", id="collections-empty")
        yield Footer()

    def on_mount(self) -> None:
        """Set the title and focus the list."""
        self.title = "Collections"
        if self._index:
            self.query_one("#collections-list", OptionList).focus()

    @staticmethod
    def _header(group: CollectionGroup) -> Text:
        """Render a group header row (collection name + count)."""
        text = Text()
        text.append(group.name, style="bold underline")
        text.append(f"  ({len(group.books)})", style="dim")
        return text

    @staticmethod
    def _format(book: Book) -> Text:
        """Render a single book row: title + path/wishlist marker."""
        text = Text()
        text.append(book.title, style="bold")
        secondary = str(book.file_path) if book.file_path is not None else "[wishlist]"
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
        if 0 <= idx < len(self._index):
            self.dismiss(self._index[idx])

    def action_cancel(self) -> None:
        """Esc / q dismisses without picking."""
        self.dismiss(None)

    def _selected(self) -> Book | None:
        try:
            lst = self.query_one("#collections-list", OptionList)
        except Exception:
            return None
        if lst.highlighted is None:
            return None
        option = lst.get_option_at_index(lst.highlighted)
        if option.id is None:
            return None
        idx = int(option.id)
        if 0 <= idx < len(self._index):
            return self._index[idx]
        return None
