"""Render chapter XHTML into a Rich :class:`Text` for the reader pane.

Deliberately not a full XHTML/CSS engine. We map a small subset of tags to
Rich styles and reflow paragraphs to the available width.

Two public entry points:

- :func:`render_chapter` — returns a single :class:`rich.text.Text` with
  ``[image: alt]`` placeholders for figures. Used by :class:`PagedView`
  where mounting widgets between paragraphs would break the two-column
  pagination.
- :func:`render_chapter_blocks` — returns a list of
  :class:`TextBlock` / :class:`ImageBlock` records. :class:`ChapterView`
  walks this to mount a Static per text block and an Image widget per
  image block (when ``Settings.images_enabled`` is on).
"""

from __future__ import annotations

import posixpath
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup, NavigableString, Tag
from rich.text import Text

from bookreader.core.exceptions import ChapterRenderError

if TYPE_CHECKING:
    from bookreader.epub.chapter import Book, Chapter

_BLOCK_TAGS = {
    "p",
    "div",
    "section",
    "article",
    "header",
    "footer",
    "blockquote",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "br",
    "hr",
    "pre",
}

_HEADING_STYLES = {
    "h1": "bold underline",
    "h2": "bold",
    "h3": "bold",
    "h4": "bold",
    "h5": "bold dim",
    "h6": "bold dim",
}


@dataclass(frozen=True, slots=True)
class TextBlock:
    """A run of rendered chapter text."""

    text: Text


@dataclass(frozen=True, slots=True)
class ImageBlock:
    """An image found in the chapter, resolved against the EPUB manifest."""

    href: str
    data: bytes
    mime: str
    alt: str


ChapterBlock = TextBlock | ImageBlock


def render_chapter(chapter: Chapter) -> Text:
    """Render *chapter* to a Rich :class:`Text` ready for display.

    Images become inline ``[image: alt]`` placeholders. Use
    :func:`render_chapter_blocks` instead when you can mount image widgets.

    Args:
        chapter: The chapter to render.

    Returns:
        A :class:`Text` with paragraph breaks and inline styles applied.

    Raises:
        ChapterRenderError: If the XHTML cannot be parsed.
    """
    try:
        soup = BeautifulSoup(chapter.html, "lxml")
    except Exception as exc:
        raise ChapterRenderError(chapter.item_id, f"parse: {exc}") from exc

    body = soup.body or soup
    out = Text()
    _walk(body, out, style="")
    return out


def render_chapter_blocks(chapter: Chapter, book: Book) -> list[ChapterBlock]:
    """Render *chapter* as alternating text and image blocks.

    Images are resolved against ``book.images`` by canonicalising the
    ``<img src>`` relative to the chapter's own href. Missing images fall
    back to a text-only ``[image: alt]`` placeholder.

    Args:
        chapter: The chapter to decompose.
        book: The parent book — supplies the image resource map.

    Returns:
        A list of blocks in document order.

    Raises:
        ChapterRenderError: If the XHTML cannot be parsed.
    """
    try:
        soup = BeautifulSoup(chapter.html, "lxml")
    except Exception as exc:
        raise ChapterRenderError(chapter.item_id, f"parse: {exc}") from exc

    body = soup.body or soup
    blocks: list[ChapterBlock] = []
    # We allocate a fresh Text per text block; ``current`` holds the
    # in-progress buffer until the next image (or the end) flushes it.
    current: list[Text] = [Text()]

    def flush() -> None:
        buf = current[0]
        if buf.plain.strip():
            blocks.append(TextBlock(text=buf))
        current[0] = Text()

    def visit(node: Tag | NavigableString, style: str) -> None:
        buf = current[0]
        if isinstance(node, NavigableString):
            text = str(node)
            if text.strip() or text == "\n":
                buf.append(text, style=style or None)
            return
        if not isinstance(node, Tag):
            return
        tag = (node.name or "").lower()
        if tag in {"script", "style", "head", "meta", "link", "nav"}:
            return
        if tag == "img":
            resolved = _resolve_image(node, chapter, book)
            if resolved is None:
                alt = node.get("alt") or "image"
                buf.append(f"[image: {alt}]\n", style="italic dim")
                return
            flush()
            blocks.append(resolved)
            return
        next_style = _style_for(tag, style)
        is_block = tag in _BLOCK_TAGS
        if is_block:
            _ensure_paragraph_break(buf)
        if tag in _HEADING_STYLES:
            for child in node.children:
                visit(child, next_style)
            current[0].append("\n\n")
            return
        if tag == "li":
            buf.append("  • ", style="dim")
        for child in node.children:
            visit(child, next_style)
        if is_block:
            current[0].append("\n")

    visit(body, "")
    flush()
    return blocks


def _resolve_image(node: Tag, chapter: Chapter, book: Book) -> ImageBlock | None:
    """Locate the EPUB resource an ``<img>`` tag points at."""
    src = node.get("src")
    if not isinstance(src, str) or not src.strip():
        return None
    alt = node.get("alt") or "image"
    # Resolve the src relative to the chapter's own location.
    chapter_dir = posixpath.dirname(chapter.href)
    candidate = posixpath.normpath(posixpath.join(chapter_dir, src.split("#", 1)[0]))
    # Try canonical (no leading ./), then the literal src in case the
    # manifest is keyed differently.
    while candidate.startswith("./"):
        candidate = candidate[2:]
    resource = book.images.get(candidate) or book.images.get(src)
    if resource is None:
        return None
    return ImageBlock(
        href=resource.href,
        data=resource.data,
        mime=resource.mime,
        alt=str(alt),
    )


def _walk(node: Tag | NavigableString, out: Text, *, style: str) -> None:
    """Depth-first traversal that emits styled text into *out*."""
    if isinstance(node, NavigableString):
        text = str(node)
        if text.strip() or text == "\n":
            out.append(text, style=style or None)
        return

    if not isinstance(node, Tag):
        return

    tag = node.name.lower() if node.name else ""

    if tag in {"script", "style", "head", "meta", "link", "nav"}:
        return

    if tag == "br":
        out.append("\n")
        return

    if tag == "hr":
        out.append("\n──────\n", style="dim")
        return

    if tag == "img":
        alt = node.get("alt") or "image"
        out.append(f"[image: {alt}]\n", style="italic dim")
        return

    next_style = _style_for(tag, style)
    is_block = tag in _BLOCK_TAGS

    if is_block:
        _ensure_paragraph_break(out)

    if tag in _HEADING_STYLES:
        for child in node.children:
            _walk(child, out, style=next_style)
        out.append("\n\n")
        return

    if tag == "li":
        out.append("  • ", style="dim")

    for child in node.children:
        _walk(child, out, style=next_style)

    if is_block:
        out.append("\n")


def _style_for(tag: str, parent: str) -> str:
    """Combine the parent style with the tag's own contribution."""
    extras: list[str] = []
    if parent:
        extras.append(parent)
    if tag in _HEADING_STYLES:
        extras.append(_HEADING_STYLES[tag])
    elif tag in {"strong", "b"}:
        extras.append("bold")
    elif tag in {"em", "i", "cite"}:
        extras.append("italic")
    elif tag == "u":
        extras.append("underline")
    elif tag == "code":
        extras.append("dim")
    elif tag == "a":
        extras.append("underline")
    elif tag == "blockquote":
        extras.append("italic dim")
    return " ".join(dict.fromkeys(extras))


def _ensure_paragraph_break(out: Text) -> None:
    """Make sure *out* ends with a blank line before starting a new block."""
    plain = out.plain
    if not plain:
        return
    trailing = plain[-2:]
    if trailing.endswith("\n\n"):
        return
    if plain.endswith("\n"):
        out.append("\n")
    else:
        out.append("\n\n")
