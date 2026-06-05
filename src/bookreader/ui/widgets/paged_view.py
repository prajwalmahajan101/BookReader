"""Two-page reading mode.

Renders the current chapter as two columns of text side by side, like an
open book. Pagination is done on the fly from the rendered Rich
:class:`Text`: at each redraw we wrap the chapter to half the available
width and slice the wrapped lines into pages of viewport height.

Pages are discrete in this mode — line scroll is meaningless. ``space`` /
``b`` advance by one *spread* (two pages); ``n`` / ``p`` and the TOC still
work as usual.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.text import Text
from textual.widgets import Static

from bookreader.epub.chapter import Chapter
from bookreader.epub.renderer import render_chapter

if TYPE_CHECKING:
    from rich.console import RenderableType


class PagedView(Static):
    """Static widget displaying a chapter as two side-by-side pages."""

    _GUTTER = 4  # cells between the two pages

    def __init__(self, *, id: str | None = None) -> None:
        """Initialize an empty paged view."""
        super().__init__(id=id)
        self._chapter_text: Text = Text()
        self._page_index: int = 0
        # Cache holds the pre-wrapped lines (one Lines per chapter render),
        # parametrised by the (width, height) they were wrapped for.
        self._cached_lines: list[Text] = []
        self._cached_col_width: int = 0
        self._cached_page_height: int = 0
        self._cached_width: int = 0
        self._cached_height: int = 0

    # ----- chapter / state -------------------------------------------------

    def show_chapter(self, chapter: Chapter, *, at_last_page: bool = False) -> None:
        """Render *chapter* and reset the page cursor.

        Args:
            chapter: The chapter to display.
            at_last_page: If true, start at the final spread (used when
                flowing backward from the next chapter).
        """
        self._chapter_text = render_chapter(chapter)
        self._invalidate_cache()
        if at_last_page:
            total = self.total_pages()
            spreads = max(1, (total + 1) // 2)
            self._page_index = (spreads - 1) * 2
        else:
            self._page_index = 0
        self.refresh(layout=True)

    def _invalidate_cache(self) -> None:
        """Drop any cached wrapping so the next render redoes the math."""
        self._cached_lines = []
        self._cached_col_width = 0
        self._cached_page_height = 0
        self._cached_width = 0
        self._cached_height = 0

    @property
    def page_index(self) -> int:
        """Index of the left page in the current spread."""
        return self._page_index

    def set_page_index(self, value: int) -> None:
        """Move directly to *value* (clamped, snapped to a spread)."""
        snapped = max(0, value - (value % 2))
        last = max(0, (self.total_pages() - 1) // 2 * 2)
        self._page_index = min(snapped, last)
        self.refresh()

    def total_pages(self) -> int:
        """Return the number of pages in the current chapter."""
        self._ensure_wrap()
        ph = self._cached_page_height
        if ph <= 0:
            return 0
        return (len(self._cached_lines) + ph - 1) // ph

    def progress(self) -> float:
        """Return chapter progress as a fraction in ``[0.0, 1.0]``."""
        total = self.total_pages()
        if total <= 0:
            return 1.0
        return min(1.0, (self._page_index + 2) / total)

    # ----- navigation ------------------------------------------------------

    def next_spread(self) -> bool:
        """Advance by one spread (two pages). Returns False at the end."""
        if self._page_index + 2 >= self.total_pages():
            return False
        self._page_index += 2
        self.refresh()
        return True

    def prev_spread(self) -> bool:
        """Retreat by one spread. Returns False at the start."""
        if self._page_index <= 0:
            return False
        self._page_index = max(0, self._page_index - 2)
        self.refresh()
        return True

    def at_start(self) -> bool:
        """True if showing the first spread."""
        return self._page_index <= 0

    def at_end(self) -> bool:
        """True if the next spread would go past the chapter."""
        return self._page_index + 2 >= self.total_pages()

    # ----- rendering -------------------------------------------------------

    def render(self) -> RenderableType:
        """Stitch the current spread line-by-line into a single :class:`Text`.

        Building the output explicitly (rather than handing two cells to a
        Rich ``Table.grid``) guarantees both columns are wrapped to exactly
        ``col_w`` cells — Rich never gets the chance to re-wrap inside a
        cell and produce uneven columns.
        """
        self._ensure_wrap()
        if not self._cached_lines or not self._cached_col_width:
            return self._chapter_text

        col_w = self._cached_col_width
        page_h = self._cached_page_height
        lines = self._cached_lines
        gap = " " * self._GUTTER
        blank = Text(" " * col_w)

        left_start = self._page_index * page_h
        right_start = left_start + page_h

        out = Text(no_wrap=True, overflow="crop")
        for row in range(page_h):
            left = _pad(lines[left_start + row], col_w) if left_start + row < len(lines) else blank
            right = (
                _pad(lines[right_start + row], col_w)
                if right_start + row < len(lines)
                else Text()
            )
            if row:
                out.append("\n")
            out.append_text(left)
            out.append(gap)
            out.append_text(right)
        return out

    # ----- pagination ------------------------------------------------------

    def _ensure_wrap(self) -> None:
        """Re-wrap the chapter text if the viewport size changed.

        Cheap enough to do on every render — Rich wraps a typical chapter
        (~2-3 thousand lines worth of source) in single-digit milliseconds.
        """
        width = self.size.width
        height = self.size.height
        if width <= 0 or height <= 0 or not self._chapter_text.plain:
            self._cached_lines = []
            self._cached_col_width = 0
            self._cached_page_height = 0
            self._cached_width = width
            self._cached_height = height
            return
        if self._cached_lines and self._cached_width == width and self._cached_height == height:
            return

        col_w = max(1, (width - self._GUTTER) // 2)
        page_h = max(1, height)
        console = Console(width=col_w, record=False, force_terminal=True)
        wrapped = list(self._chapter_text.wrap(console, col_w))

        self._cached_lines = wrapped
        self._cached_col_width = col_w
        self._cached_page_height = page_h
        self._cached_width = width
        self._cached_height = height

    # ----- size hook -------------------------------------------------------

    def on_resize(self) -> None:
        """Invalidate the page cache when the viewport changes size."""
        self._invalidate_cache()
        self.refresh()


def _pad(line: Text, width: int) -> Text:
    """Right-pad *line* to exactly *width* cells without mutating it."""
    plain = line.plain
    if len(plain) >= width:
        return line
    out = line.copy()
    out.append(" " * (width - len(plain)))
    return out
