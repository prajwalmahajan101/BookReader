"""EPUB parsing and rendering.

Pure layer: no UI, no persistence. Public types are :class:`Chapter`,
:class:`TocEntry`, :class:`Book`, and the :func:`open_book` entry point.
"""

from __future__ import annotations

from bookreader.epub.chapter import Book, Chapter, TocEntry
from bookreader.epub.reader import open_book
from bookreader.epub.renderer import render_chapter

__all__ = ["Book", "Chapter", "TocEntry", "open_book", "render_chapter"]
