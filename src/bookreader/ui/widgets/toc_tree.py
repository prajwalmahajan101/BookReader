"""Table-of-contents sidebar.

Uses Textual's :class:`OptionList` (flat, jumpable, virtualizes) rather than
:class:`Tree` — the flat list with indented labels reads faster for a book
TOC and avoids accidental collapsing.
"""

from __future__ import annotations

from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from bookreader.epub.chapter import TocEntry


class TocTree(OptionList):
    """Flat, jumpable table of contents.

    Emits :class:`TocTree.Selected` when the user picks an entry.
    """

    class Selected(Message):
        """Posted when the user activates a TOC entry.

        Attributes:
            chapter_index: Spine index to jump to.
        """

        def __init__(self, chapter_index: int) -> None:
            """Initialize with the destination chapter index."""
            self.chapter_index = chapter_index
            super().__init__()

    def __init__(self, entries: tuple[TocEntry, ...]) -> None:
        """Initialize with the book's flattened TOC."""
        self._entries = entries
        options = [Option(self._format(entry), id=str(i)) for i, entry in enumerate(entries)]
        super().__init__(*options, id="toc-list")

    @staticmethod
    def _format(entry: TocEntry) -> str:
        """Indent by depth and prefix top-level entries with a bullet."""
        indent = "  " * entry.depth
        bullet = "• " if entry.depth == 0 else ""
        return f"{indent}{bullet}{entry.label}"

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Translate the option event into a :class:`Selected` message."""
        if event.option.id is None:
            return
        idx = int(event.option.id)
        if 0 <= idx < len(self._entries):
            self.post_message(self.Selected(self._entries[idx].chapter_index))
