"""EPUB parsing and rendering.

Pure layer: no UI, no persistence. Public types are :class:`Chapter`,
:class:`TocEntry`, :class:`Book`, and the :func:`open_book` entry point.
"""

from __future__ import annotations

import warnings

from bs4 import XMLParsedAsHTMLWarning

from bookreader.epub.chapter import Book, Chapter, TocEntry
from bookreader.epub.reader import open_book
from bookreader.epub.renderer import render_chapter

# XHTML chapters are valid HTML; the lxml HTML parser handles them correctly.
# Suppress BeautifulSoup's "you should use the XML parser" advice.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

__all__ = ["Book", "Chapter", "TocEntry", "open_book", "render_chapter"]
