"""The reading pane.

In Phase 1 this was a single :class:`Static` rendering the entire chapter.
Phase 3 widens it into a vertical container of alternating text blocks and
image widgets so figures render inline when the terminal supports kitty,
iterm, or sixel graphics (via :mod:`textual_image`). The parent screen
wraps the whole thing in a ``VerticalScroll`` so scrolling Just Works.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static

from bookreader.core.config import _terminal_supports_graphics, load_settings
from bookreader.core.logging import get_logger
from bookreader.epub.renderer import (
    ImageBlock,
    TextBlock,
    render_chapter,
    render_chapter_blocks,
)

if TYPE_CHECKING:
    from bookreader.epub.chapter import Book, Chapter

log = get_logger(__name__)


class ChapterView(Vertical):
    """A vertical container of text and image widgets for one chapter."""

    DEFAULT_CSS = """
    ChapterView {
        width: 100%;
        height: auto;
    }
    ChapterView > Static {
        width: 100%;
        height: auto;
    }
    /* textual-image widgets default to ``height: 1fr`` which makes them
     * expand to consume all remaining vertical space — that pushes the
     * text below the image off the visible page. Pin height to ``auto``
     * so the widget sizes to its image's natural aspect ratio at the
     * available column width, and let scroll handle the rest. */
    ChapterView Image, ChapterView AutoImage {
        width: 100%;
        height: auto;
        margin: 1 0;
    }
    """

    def __init__(self, *, id: str | None = None) -> None:
        """Initialize empty; :meth:`show_chapter` populates the tree."""
        super().__init__(id=id)
        self._settings = load_settings()
        self._book: Book | None = None
        self._last_chapter: Chapter | None = None
        # One-shot per session: once we've nudged the user about
        # disabled images on a capable terminal, stay quiet.
        self._image_hint_shown: bool = False

    def attach_book(self, book: Book) -> None:
        """Tell the view which book it belongs to (for image resolution)."""
        self._book = book

    @property
    def images_enabled(self) -> bool:
        """Whether inline image rendering is currently active."""
        return self._settings.images_enabled

    def set_images_enabled(self, value: bool) -> None:
        """Flip the in-memory image toggle. Caller should repaint."""
        self._settings.images_enabled = value

    def show_chapter(self, chapter: Chapter) -> None:
        """Replace contents with a fresh render of *chapter*.

        Returns synchronously — Textual completes the mount/remove work on
        the next compositor tick. Awaiting is unnecessary because the
        caller refreshes the layout afterward anyway.
        """
        # Tear down whatever's there. The await-able returned by
        # ``remove_children`` is discarded — the operation still runs.
        self.remove_children()
        if self._book is None:
            # No book context → fall back to a single Static so tests and
            # any detached usage keep working.
            self.mount(Static(render_chapter(chapter)))
            return
        try:
            blocks = render_chapter_blocks(chapter, self._book)
        except Exception as exc:  # log but never crash the reader
            log.warning("block render failed: %s", exc)
            self.mount(Static(render_chapter(chapter)))
            return

        widgets: list[Widget] = []
        image_block_count = 0
        for block in blocks:
            if isinstance(block, TextBlock):
                widgets.append(Static(block.text))
            elif isinstance(block, ImageBlock):
                image_block_count += 1
                widgets.append(self._build_image_widget(block))
        if widgets:
            self.mount_all(widgets)

        # Discoverability: if the chapter had images, the terminal can draw
        # them, and the user has them disabled, fire one quiet nudge.
        if (
            image_block_count
            and not self._settings.images_enabled
            and _terminal_supports_graphics()
            and not self._image_hint_shown
        ):
            self._image_hint_shown = True
            self.notify(
                "Inline images available — press I to enable",
                timeout=4,
            )

    def _build_image_widget(self, block: ImageBlock) -> Widget:
        """Return an image widget when supported, else a placeholder."""
        if not self._settings.images_enabled:
            return Static(f"[image: {block.alt}]", classes="image-placeholder")
        try:
            from PIL import Image as PILImage
            from textual_image.widget import Image

            img = PILImage.open(io.BytesIO(block.data))
            return Image(img)
        except Exception as exc:  # missing deps or unsupported terminal
            log.warning("image widget failed (%s): falling back to text", exc)
            return Static(f"[image: {block.alt}]", classes="image-placeholder")
