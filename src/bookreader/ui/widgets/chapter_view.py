"""The reading pane.

A :class:`Static` rendering the current chapter's :class:`rich.text.Text`.
Wrapped in a Textual ``VerticalScroll`` by the parent screen so scroll state
(arrow keys, ``j``/``k``, page up/down) comes for free.
"""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from bookreader.epub.chapter import Chapter
from bookreader.epub.renderer import render_chapter


class ChapterView(Static):
    """Static widget showing one rendered chapter at a time."""

    def show_chapter(self, chapter: Chapter) -> None:
        """Render *chapter* and replace the widget's content."""
        rendered: Text = render_chapter(chapter)
        self.update(rendered)
