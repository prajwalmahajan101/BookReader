"""Sidebar collection picker for the library screen.

Renders three groups (top entries, the user's collections, bottom entries)
in one :class:`OptionList`. Emits :class:`CollectionList.Selected` with a
:class:`CollectionFilter` describing the picked entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from rich.text import Text
from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from collections.abc import Iterable

    from bookreader.library.models import Collection


FilterKind = Literal["all", "recents", "collection"]


@dataclass(frozen=True, slots=True)
class CollectionFilter:
    """Describes which slice of the library to show in the main table.

    Attributes:
        kind: One of ``"all"``, ``"recents"``, or ``"collection"``.
        collection_id: Only set when ``kind == "collection"``.
        label: Display label, useful for the status strip.
    """

    kind: FilterKind
    collection_id: int | None
    label: str


_ALL = CollectionFilter(kind="all", collection_id=None, label="All books")
_RECENTS = CollectionFilter(kind="recents", collection_id=None, label="Recents")


class CollectionList(OptionList):
    """Sidebar listing virtual filters + user collections + counts."""

    class Selected(Message):
        """Posted when the user activates a filter."""

        def __init__(self, choice: CollectionFilter) -> None:
            """Initialize with the chosen filter."""
            self.choice = choice
            super().__init__()

    def __init__(self, *, id: str | None = None) -> None:
        """Initialize empty; ``set_state`` populates rows."""
        super().__init__(id=id)
        self._entries: list[CollectionFilter] = []

    def set_state(
        self,
        *,
        collections: Iterable[Collection],
        total_books: int,
        recent_count: int,
        per_collection: dict[int, int],
    ) -> None:
        """Rebuild the list with current counts."""
        self.clear_options()
        self._entries = []

        def add(label: str, count: int, choice: CollectionFilter) -> None:
            self._entries.append(choice)
            self.add_option(Option(self._format(label, count), id=str(len(self._entries) - 1)))

        add("All books", total_books, _ALL)
        for col in collections:
            count = per_collection.get(col.id, 0)
            add(
                col.name,
                count,
                CollectionFilter(
                    kind="collection",
                    collection_id=col.id,
                    label=col.name,
                ),
            )
        add("Recents", recent_count, _RECENTS)

        if self._entries:
            self.highlighted = 0

    @staticmethod
    def _format(label: str, count: int) -> Text:
        """Render `Label              N`, right-padded count."""
        text = Text()
        text.append(label)
        text.append(f"  {count}", style="dim")
        return text

    def current_filter(self) -> CollectionFilter:
        """Return the currently highlighted filter (defaults to All)."""
        if not self._entries:
            return _ALL
        idx = self.highlighted or 0
        return self._entries[idx]

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Translate the option event into :class:`Selected`."""
        if event.option.id is None:
            return
        idx = int(event.option.id)
        if 0 <= idx < len(self._entries):
            self.post_message(self.Selected(self._entries[idx]))
