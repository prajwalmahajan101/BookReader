"""Tests for ``render_chapter_blocks`` — text + image decomposition."""

from __future__ import annotations

from pathlib import Path

from bookreader.epub.chapter import Book, Chapter, ImageResource
from bookreader.epub.renderer import ImageBlock, TextBlock, render_chapter_blocks


def _book_with_image(html: str, image_href: str) -> Book:
    chapter = Chapter(
        index=0,
        item_id="c0",
        href="OEBPS/Text/chap.xhtml",
        title="X",
        html=html,
    )
    images = {image_href: ImageResource(href=image_href, data=b"FAKE", mime="image/png")}
    return Book(
        path=Path("/tmp/x.epub"),
        identifier="test",
        title="T",
        authors=(),
        chapters=(chapter,),
        toc=(),
        images=images,
    )


def test_emits_text_then_image_then_text() -> None:
    book = _book_with_image(
        "<html><body><p>before</p>"
        '<img src="../Images/cover.png" alt="cover">'
        "<p>after</p></body></html>",
        image_href="OEBPS/Images/cover.png",
    )
    blocks = render_chapter_blocks(book.chapters[0], book)
    assert len(blocks) == 3
    assert isinstance(blocks[0], TextBlock)
    assert "before" in blocks[0].text.plain
    assert isinstance(blocks[1], ImageBlock)
    assert blocks[1].alt == "cover"
    assert blocks[1].data == b"FAKE"
    assert isinstance(blocks[2], TextBlock)
    assert "after" in blocks[2].text.plain


def test_unresolved_image_falls_back_to_placeholder_inside_text() -> None:
    book = _book_with_image(
        '<html><body><p>x</p><img src="nope.png" alt="missing"><p>y</p></body></html>',
        image_href="OEBPS/Images/different.png",
    )
    blocks = render_chapter_blocks(book.chapters[0], book)
    # No ImageBlock — placeholder text lives inside a TextBlock
    assert all(isinstance(b, TextBlock) for b in blocks)
    combined = "\n".join(b.text.plain for b in blocks if isinstance(b, TextBlock))
    assert "[image: missing]" in combined


def test_text_only_chapter_returns_single_block() -> None:
    book = _book_with_image(
        "<html><body><h1>A</h1><p>Body.</p></body></html>",
        image_href="x.png",
    )
    blocks = render_chapter_blocks(book.chapters[0], book)
    assert len(blocks) == 1
    assert isinstance(blocks[0], TextBlock)
