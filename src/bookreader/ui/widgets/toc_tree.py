"""Table-of-contents sidebar.

A flat :class:`OptionList` indented by depth. The widget owns its own
``current chapter`` state and re-styles the matching row whenever it
changes, so the user always sees where they are reading.
"""

from __future__ import annotations

from rich.text import Text
from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from bookreader.epub.chapter import TocEntry

_MARKER_CURRENT = "▶ "
_MARKER_IDLE = "  "


class TocTree(OptionList):
    """Flat, jumpable table of contents with a "current chapter" marker."""

    class Selected(Message):
        """Posted when the user activates a TOC entry.

        Attributes:
            chapter_index: Spine index to jump to.
        """

        def __init__(self, chapter_index: int) -> None:
            """Initialize with the destination chapter index."""
            self.chapter_index = chapter_index
            super().__init__()

    def __init__(self, entries: tuple[TocEntry, ...], *, id: str | None = None) -> None:
        """Initialize with the book's flattened TOC.

        Args:
            entries: Flattened TOC rows to display.
            id: DOM id for the widget, forwarded to ``OptionList``.
        """
        self._entries = entries
        self._current_chapter_index: int | None = None
        options = [
            Option(self._render(entry, current=False), id=str(i)) for i, entry in enumerate(entries)
        ]
        super().__init__(*options, id=id)

    def set_current_chapter(self, chapter_index: int) -> None:
        """Highlight the TOC row that points to *chapter_index*.

        If the chapter does not appear in the TOC (incomplete metadata)
        nothing changes.
        """
        target_row = self._row_for_chapter(chapter_index)
        if target_row is None:
            return
        previous_row = (
            self._row_for_chapter(self._current_chapter_index)
            if self._current_chapter_index is not None
            else None
        )
        self._current_chapter_index = chapter_index

        if previous_row is not None and previous_row != target_row:
            self.replace_option_prompt_at_index(
                previous_row,
                self._render(self._entries[previous_row], current=False),
            )
        self.replace_option_prompt_at_index(
            target_row,
            self._render(self._entries[target_row], current=True),
        )
        # Move the cursor to the current chapter so the user lands there
        # whenever the sidebar is focused.
        self.highlighted = target_row

    def _row_for_chapter(self, chapter_index: int | None) -> int | None:
        """Return the TOC row whose ``chapter_index`` matches *chapter_index*."""
        if chapter_index is None:
            return None
        for row, entry in enumerate(self._entries):
            if entry.chapter_index == chapter_index:
                return row
        return None

    @staticmethod
    def _render(entry: TocEntry, *, current: bool) -> Text:
        """Render a TOC row with depth indentation and a current-marker."""
        indent = "  " * entry.depth
        marker = _MARKER_CURRENT if current else _MARKER_IDLE
        text = Text()
        text.append(indent)
        text.append(marker, style="bold" if current else "dim")
        text.append(entry.label, style="bold" if current else "")
        return text

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Translate the option event into a :class:`Selected` message."""
        if event.option.id is None:
            return
        idx = int(event.option.id)
        if 0 <= idx < len(self._entries):
            self.post_message(self.Selected(self._entries[idx].chapter_index))
