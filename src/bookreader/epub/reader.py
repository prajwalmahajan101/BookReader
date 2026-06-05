"""Open an EPUB and produce a :class:`Book`.

Wraps :mod:`ebooklib` so the rest of the app never imports it. Any failure
during parsing raises :class:`EpubParseError` with the source path attached.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ebooklib import ITEM_DOCUMENT, epub

from bookreader.core.exceptions import EpubParseError
from bookreader.core.logging import get_logger
from bookreader.epub.chapter import Book, Chapter, TocEntry

if TYPE_CHECKING:
    from collections.abc import Iterable

log = get_logger(__name__)


def open_book(path: Path) -> Book:
    """Open *path* and return a fully-parsed :class:`Book`.

    Args:
        path: Filesystem path to an ``.epub`` file.

    Returns:
        A :class:`Book` populated with spine chapters and table of contents.

    Raises:
        EpubParseError: If the file cannot be opened or has no spine.
    """
    if not path.exists():
        raise EpubParseError(path, "file does not exist")

    try:
        book = epub.read_epub(str(path))
    except Exception as exc:  # ebooklib raises a variety of types
        raise EpubParseError(path, f"ebooklib: {exc}") from exc

    chapters = _extract_chapters(book)
    if not chapters:
        raise EpubParseError(path, "no readable chapters found in spine")

    identifier = _identifier(book, path)
    title = _first_metadata(book, "DC", "title") or path.stem
    authors = tuple(_all_metadata(book, "DC", "creator"))
    toc = tuple(_flatten_toc(book.toc, chapters))

    log.info("opened EPUB %s (%d chapters, id=%s)", path, len(chapters), identifier)
    return Book(
        path=path,
        identifier=identifier,
        title=title,
        authors=authors,
        chapters=tuple(chapters),
        toc=toc,
    )


def _extract_chapters(book: epub.EpubBook) -> list[Chapter]:
    """Walk the spine in order and build :class:`Chapter` records.

    Skips the ``nav`` document and any item marked with ``properties=nav`` —
    EPUB 3 navigation isn't reading content.
    """
    chapters: list[Chapter] = []
    for item_id, _linear in book.spine:
        if item_id == "nav":
            continue
        item = book.get_item_with_id(item_id)
        if item is None or item.get_type() != ITEM_DOCUMENT:
            continue
        if "nav" in (item.properties or []):
            continue
        html = item.get_content().decode("utf-8", errors="replace")
        chapters.append(
            Chapter(
                index=len(chapters),
                item_id=item_id,
                href=item.get_name(),
                title=_chapter_title(html, len(chapters)),
                html=html,
            )
        )
    return chapters


def _chapter_title(html: str, index: int) -> str:
    """Best-effort title extraction from the first heading in the chapter."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    for tag in ("h1", "h2", "h3", "title"):
        node = soup.find(tag)
        if node and node.get_text(strip=True):
            return node.get_text(strip=True)
    return f"Chapter {index + 1}"


def _identifier(book: epub.EpubBook, path: Path) -> str:
    """Return ``dc:identifier`` if present, else a SHA-1 of file bytes."""
    ident = _first_metadata(book, "DC", "identifier")
    if ident:
        return ident
    return "sha1:" + hashlib.sha1(path.read_bytes()).hexdigest()


def _first_metadata(book: epub.EpubBook, namespace: str, name: str) -> str | None:
    """Return the first ``(value, attrs)`` text for a metadata field."""
    items = cast("list[tuple[str, dict[str, Any]]]", book.get_metadata(namespace, name))
    if not items:
        return None
    value, _attrs = items[0]
    return value or None


def _all_metadata(book: epub.EpubBook, namespace: str, name: str) -> Iterable[str]:
    """Yield non-empty values for repeated metadata fields."""
    items = cast("list[tuple[str, dict[str, Any]]]", book.get_metadata(namespace, name))
    for value, _attrs in items:
        if value:
            yield value


def _flatten_toc(
    raw_toc: Any,
    chapters: list[Chapter],
) -> list[TocEntry]:
    """Flatten ebooklib's nested TOC into ``(label, chapter_index, depth)`` rows."""
    by_href = {c.href: c.index for c in chapters}
    flat: list[TocEntry] = []

    def visit(node: Any, depth: int) -> None:
        # ebooklib TOC nodes are either epub.Link, tuples (section, children),
        # or lists. Normalize.
        if isinstance(node, tuple) and len(node) == 2:
            section, children = node
            label = getattr(section, "title", None) or str(section)
            href = getattr(section, "href", "")
            idx = _resolve_href(href, by_href)
            if idx is not None:
                flat.append(TocEntry(label=label, chapter_index=idx, depth=depth))
            for child in children or []:
                visit(child, depth + 1)
        elif isinstance(node, list):
            for child in node:
                visit(child, depth)
        else:
            label = getattr(node, "title", None) or str(node)
            href = getattr(node, "href", "")
            idx = _resolve_href(href, by_href)
            if idx is not None:
                flat.append(TocEntry(label=label, chapter_index=idx, depth=depth))

    visit(raw_toc, 0)
    return flat


def _resolve_href(href: str, by_href: dict[str, int]) -> int | None:
    """Resolve a TOC href (possibly with ``#anchor``) to a spine index."""
    if not href:
        return None
    base = href.split("#", 1)[0]
    return by_href.get(base) or by_href.get(href)
