"""Render chapter XHTML into a Rich :class:`Text` for the reader pane.

Deliberately not a full XHTML/CSS engine. We map a small subset of tags to
Rich styles and reflow paragraphs to the available width. Images become an
``[image: alt]`` placeholder in Phase 1.

The output is a Rich renderable — the UI wraps it in a Textual ``Static``
widget. This keeps the renderer unit-testable without spinning up an app.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup, NavigableString, Tag
from rich.text import Text

from bookreader.core.exceptions import ChapterRenderError

if TYPE_CHECKING:
    from bookreader.epub.chapter import Chapter

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


def render_chapter(chapter: Chapter) -> Text:
    """Render *chapter* to a Rich :class:`Text` ready for display.

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


