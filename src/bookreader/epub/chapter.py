"""Dataclasses describing a parsed EPUB.

These types are deliberately framework-agnostic so they can flow into the
renderer and the UI without leaking ebooklib internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Chapter:
    """A single spine item in reading order.

    Attributes:
        index: Zero-based position in the spine.
        item_id: Manifest id from the EPUB OPF file.
        href: Internal href (used to resolve TOC anchors).
        title: Best-effort chapter title — falls back to ``Chapter N``.
        html: Raw XHTML body of the chapter.
    """

    index: int
    item_id: str
    href: str
    title: str
    html: str


@dataclass(frozen=True, slots=True)
class TocEntry:
    """One row in the table of contents.

    Attributes:
        label: Display label.
        chapter_index: Spine index this entry jumps to.
        depth: Nesting level (0 for top-level entries).
    """

    label: str
    chapter_index: int
    depth: int = 0


@dataclass(frozen=True, slots=True)
class Book:
    """A loaded EPUB ready to render.

    Attributes:
        path: Source file path.
        identifier: Stable id (``dc:identifier`` from OPF, or a SHA-1
            fallback computed from file bytes).
        title: Book title.
        authors: Tuple of author names.
        chapters: Spine, in reading order.
        toc: Flattened table of contents.
    """

    path: Path
    identifier: str
    title: str
    authors: tuple[str, ...]
    chapters: tuple[Chapter, ...]
    toc: tuple[TocEntry, ...] = field(default_factory=tuple)
