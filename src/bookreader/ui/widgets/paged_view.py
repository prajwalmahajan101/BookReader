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
from rich.table import Table
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
        self._cached_pages: tuple[Text, ...] = ()
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
        self._cached_pages = ()
        self._cached_width = 0
        self._cached_height = 0
        if at_last_page:
            pages = self._paginate()
            spreads = max(1, (len(pages) + 1) // 2)
            self._page_index = (spreads - 1) * 2
        else:
            self._page_index = 0
        self.refresh(layout=True)

    @property
    def page_index(self) -> int:
        """Index of the left page in the current spread."""
        return self._page_index

    def set_page_index(self, value: int) -> None:
        """Move directly to *value* (clamped, snapped to a spread)."""
        snapped = max(0, value - (value % 2))
        last = max(0, (len(self._paginate()) - 1) // 2 * 2)
        self._page_index = min(snapped, last)
        self.refresh()

    def total_pages(self) -> int:
        """Return the number of pages in the current chapter."""
        return len(self._paginate())

    def progress(self) -> float:
        """Return chapter progress as a fraction in ``[0.0, 1.0]``."""
        total = self.total_pages()
        if total <= 0:
            return 1.0
        return min(1.0, (self._page_index + 2) / total)

    # ----- navigation ------------------------------------------------------

    def next_spread(self) -> bool:
        """Advance by one spread (two pages). Returns False at the end."""
        pages = self._paginate()
        if self._page_index + 2 >= len(pages):
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
        return self._page_index + 2 >= len(self._paginate())

    # ----- rendering -------------------------------------------------------

    def render(self) -> RenderableType:
        """Build a two-column Table.grid with the current spread."""
        pages = self._paginate()
        if not pages or self.size.width == 0:
            return self._chapter_text

        idx = self._page_index
        left = pages[idx] if idx < len(pages) else Text("")
        right = pages[idx + 1] if idx + 1 < len(pages) else Text("")

        grid = Table.grid(padding=(0, self._GUTTER // 2), expand=True)
        grid.add_column(ratio=1, no_wrap=False, overflow="fold")
        grid.add_column(ratio=1, no_wrap=False, overflow="fold")
        grid.add_row(left, right)
        return grid

    # ----- pagination ------------------------------------------------------

    def _paginate(self) -> tuple[Text, ...]:
        """Cache-aware split of the chapter text into page-sized chunks.

        Re-wraps and re-slices whenever the viewport size changes. Each page
        is itself a Rich :class:`Text` joined back from its wrapped lines so
        original styling is preserved.
        """
        width = self.size.width
        height = self.size.height
        if width <= 0 or height <= 0 or not self._chapter_text.plain:
            return ()
        if (
            self._cached_pages
            and self._cached_width == width
            and self._cached_height == height
        ):
            return self._cached_pages

        page_width = max(1, (width - self._GUTTER) // 2)
        page_height = max(1, height)
        console = Console(width=page_width, record=False, force_terminal=True)
        wrapped = self._chapter_text.wrap(console, page_width)
        # `wrapped` is a `Lines` (a list of Text). Slice by page_height.
        pages: list[Text] = []
        for start in range(0, len(wrapped), page_height):
            slice_lines = list(wrapped[start : start + page_height])
            page = Text()
            for i, line in enumerate(slice_lines):
                if i:
                    page.append("\n")
                page.append_text(line)
            pages.append(page)

        self._cached_pages = tuple(pages)
        self._cached_width = width
        self._cached_height = height
        return self._cached_pages

    # ----- size hook -------------------------------------------------------

    def on_resize(self) -> None:
        """Invalidate the page cache when the viewport changes size."""
        self._cached_pages = ()
        self._cached_width = 0
        self._cached_height = 0
        self.refresh()
