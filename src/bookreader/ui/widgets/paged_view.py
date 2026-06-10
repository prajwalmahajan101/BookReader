"""Two-page reading mode with mounted widgets.

The original PagedView pre-paginated a flat Rich :class:`Text` and
rendered the current spread as a single string. That made image
support impossible — Textual needs Image widgets in the layout tree,
not escape sequences inside a Static.

This rewrite walks the chapter as a list of :class:`ChapterBlock`
records (the same source the scroll view consumes) and builds each
page as a slice of those blocks. The spread is mounted as a
``Horizontal`` of two ``Vertical`` columns; each column gets ``Static``
widgets for text blocks and ``textual_image`` widgets for image
blocks. Pagination becomes "which blocks fit on this page" rather than
"which wrapped lines fit on this page" — the trade-off is a slightly
less precise line count, but in return we get inline images at full
quality inside the spread.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from rich.console import Console
from rich.text import Text
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Static

from bookreader.core.config import load_settings
from bookreader.core.logging import get_logger
from bookreader.epub.chapter import Chapter
from bookreader.epub.renderer import (
    ChapterBlock,
    ImageBlock,
    TextBlock,
    render_chapter,
    render_chapter_blocks,
)

if TYPE_CHECKING:
    from bookreader.epub.chapter import Book

log = get_logger(__name__)


class PagedView(Vertical):
    """Two-column paged view that mounts widgets per spread.

    Public API mirrors the prior Static-based version so the reader
    screen needs no changes: :meth:`show_chapter`, :meth:`page_index`,
    :meth:`set_page_index`, :meth:`total_pages`, :meth:`next_spread`,
    :meth:`prev_spread`, :meth:`at_start`, :meth:`at_end`,
    :meth:`progress`. New: :meth:`attach_book` (needed for image
    resolution; mirrors :class:`ChapterView`).
    """

    _GUTTER = 4  # cells between the two pages
    _IMAGE_PAGE_FRACTION = 0.6  # an image consumes ~60% of a page

    DEFAULT_CSS = """
    PagedView {
        width: 100%;
        height: 1fr;
    }
    PagedView #spread {
        width: 100%;
        height: 1fr;
        layout: horizontal;
    }
    PagedView .paged-column {
        width: 1fr;
        height: 1fr;
        padding: 0 1;
        overflow: hidden;
    }
    PagedView .paged-gutter {
        width: 4;
        height: 1fr;
    }
    PagedView Image, PagedView AutoImage {
        width: auto;
        height: auto;
        max-width: 100%;
        margin: 1 0;
    }
    PagedView Static {
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, *, id: str | None = None) -> None:
        """Initialize an empty paged view."""
        super().__init__(id=id)
        self._book: Book | None = None
        self._blocks: list[ChapterBlock] = []
        self._pages: list[list[ChapterBlock]] = []
        self._page_index: int = 0
        self._cached_col_width: int = 0
        self._cached_page_height: int = 0
        self._settings = load_settings()

    # ----- book / chapter -------------------------------------------------

    def attach_book(self, book: Book) -> None:
        """Provide the book context so images can be resolved."""
        self._book = book

    def show_chapter(self, chapter: Chapter, *, at_last_page: bool = False) -> None:
        """Decompose *chapter* into blocks, paginate, mount the spread."""
        if self._book is not None:
            try:
                self._blocks = render_chapter_blocks(chapter, self._book)
            except Exception as exc:
                log.warning("paged block render failed: %s", exc)
                self._blocks = [TextBlock(text=render_chapter(chapter))]
        else:
            self._blocks = [TextBlock(text=render_chapter(chapter))]

        self._paginate()
        if at_last_page:
            self._page_index = max(0, (len(self._pages) - 1) // 2 * 2)
        else:
            self._page_index = 0
        self._render_spread()

    # ----- pagination -----------------------------------------------------

    def _paginate(self) -> None:
        """Split ``self._blocks`` into pages that fit ``(col_w, page_h)``.

        Text blocks are wrapped to ``col_w`` and chopped at page-height
        boundaries (a single TextBlock can therefore appear on multiple
        pages — we slice the wrapped lines). Image blocks are atomic:
        they take ``~_IMAGE_PAGE_FRACTION`` of a page; if the current
        page can't fit one, we commit it and start a new page.
        """
        width = max(20, self.size.width or 80)
        height = max(4, self.size.height or 24)
        col_w = max(20, (width - self._GUTTER) // 2)
        page_h = height
        self._cached_col_width = col_w
        self._cached_page_height = page_h

        pages: list[list[ChapterBlock]] = [[]]
        used_h = 0
        console = Console(width=col_w, record=False, force_terminal=True)
        image_h = max(4, int(page_h * self._IMAGE_PAGE_FRACTION))

        def commit_and_reset() -> None:
            nonlocal used_h
            pages.append([])
            used_h = 0

        for block in self._blocks:
            if isinstance(block, TextBlock):
                wrapped = list(block.text.wrap(console, col_w))
                i = 0
                while i < len(wrapped):
                    remaining = page_h - used_h
                    if remaining <= 0:
                        commit_and_reset()
                        remaining = page_h
                    take = wrapped[i : i + remaining]
                    chunk = Text("\n").join(take)
                    pages[-1].append(TextBlock(text=chunk))
                    used_h += len(take)
                    i += len(take)
            elif isinstance(block, ImageBlock):
                if used_h + image_h > page_h and pages[-1]:
                    commit_and_reset()
                pages[-1].append(block)
                used_h += image_h

        # Drop a trailing empty page so total_pages is accurate.
        if pages and not pages[-1]:
            pages.pop()
        self._pages = pages or [[]]

    def _needs_repaginate(self) -> bool:
        """True when the cached pagination doesn't match the current size."""
        width = max(20, self.size.width or 80)
        height = max(4, self.size.height or 24)
        col_w = max(20, (width - self._GUTTER) // 2)
        return col_w != self._cached_col_width or height != self._cached_page_height

    # ----- spread rendering -----------------------------------------------

    def _render_spread(self) -> None:
        """Tear down children and re-mount the current pair of pages."""
        self.remove_children()
        spread = Horizontal(id="spread")
        self.mount(spread)
        left = Vertical(classes="paged-column", id="left-page")
        gutter = Static("", classes="paged-gutter")
        right = Vertical(classes="paged-column", id="right-page")
        spread.mount(left, gutter, right)
        for widget in self._page_widgets(self._page_index):
            left.mount(widget)
        for widget in self._page_widgets(self._page_index + 1):
            right.mount(widget)

    def _page_widgets(self, idx: int) -> list[Widget]:
        """Return the mounted widgets for page *idx* (empty if past end)."""
        if idx < 0 or idx >= len(self._pages):
            return []
        widgets: list[Widget] = []
        for block in self._pages[idx]:
            if isinstance(block, TextBlock):
                widgets.append(Static(block.text))
            elif isinstance(block, ImageBlock):
                widgets.append(self._build_image_widget(block))
        return widgets

    def _build_image_widget(self, block: ImageBlock) -> Widget:
        """Return an image widget when supported, else a placeholder."""
        if not self._settings.images_enabled:
            return Static(f"[image: {block.alt}]", classes="image-placeholder")
        try:
            from PIL import Image as PILImage
            from textual_image.widget import Image

            img = PILImage.open(io.BytesIO(block.data))
            return Image(img)
        except Exception as exc:
            log.warning("paged image widget failed (%s): falling back to text", exc)
            return Static(f"[image: {block.alt}]", classes="image-placeholder")

    # ----- navigation -----------------------------------------------------

    @property
    def page_index(self) -> int:
        """Index of the left page in the current spread."""
        return self._page_index

    def set_page_index(self, value: int) -> None:
        """Move directly to *value* (clamped, snapped to a spread)."""
        snapped = max(0, value - (value % 2))
        last = max(0, (self.total_pages() - 1) // 2 * 2)
        self._page_index = min(snapped, last)
        self._render_spread()

    def total_pages(self) -> int:
        """Return the number of pages in the current chapter."""
        return len(self._pages)

    def progress(self) -> float:
        """Return chapter progress as a fraction in ``[0.0, 1.0]``."""
        total = self.total_pages()
        if total <= 0:
            return 1.0
        return min(1.0, (self._page_index + 2) / total)

    def next_spread(self) -> bool:
        """Advance by one spread. Returns False at the end."""
        if self._page_index + 2 >= self.total_pages():
            return False
        self._page_index += 2
        self._render_spread()
        return True

    def prev_spread(self) -> bool:
        """Retreat by one spread. Returns False at the start."""
        if self._page_index <= 0:
            return False
        self._page_index = max(0, self._page_index - 2)
        self._render_spread()
        return True

    def at_start(self) -> bool:
        """True if showing the first spread."""
        return self._page_index <= 0

    def at_end(self) -> bool:
        """True if the next spread would go past the chapter."""
        return self._page_index + 2 >= self.total_pages()

    # ----- size hook ------------------------------------------------------

    def on_resize(self) -> None:
        """Re-paginate + re-render when the viewport changes size."""
        if self._needs_repaginate() and self._blocks:
            # Preserve roughly-the-same reading position across resize by
            # remembering the fractional progress and rounding to the
            # nearest spread on the new pagination.
            progress = self.progress() if self._pages else 0.0
            self._paginate()
            new_total = self.total_pages()
            target = int(progress * max(0, new_total - 1))
            self._page_index = max(0, target - (target % 2))
            self._render_spread()
