"""Tests for ``bookreader.epub.renderer``."""

from __future__ import annotations

from bookreader.epub.chapter import Chapter
from bookreader.epub.renderer import render_chapter


def _chapter(html: str) -> Chapter:
    return Chapter(index=0, item_id="x", href="x.xhtml", title="X", html=html)


def test_render_emits_paragraph_text() -> None:
    text = render_chapter(_chapter("<html><body><p>Hello world</p></body></html>"))
    assert "Hello world" in text.plain


def test_render_preserves_emphasis_text() -> None:
    text = render_chapter(_chapter("<html><body><p>be <strong>bold</strong> now</p></body></html>"))
    assert "bold" in text.plain


def test_render_inserts_image_placeholder() -> None:
    text = render_chapter(_chapter('<html><body><img src="x.png" alt="cover art"></body></html>'))
    assert "[image: cover art]" in text.plain


def test_render_drops_script_and_style() -> None:
    text = render_chapter(
        _chapter(
            "<html><body>"
            "<script>alert(1)</script>"
            "<style>body{color:red}</style>"
            "<p>visible</p>"
            "</body></html>"
        )
    )
    assert "alert" not in text.plain
    assert "color:red" not in text.plain
    assert "visible" in text.plain


def test_render_headings_emit_text() -> None:
    text = render_chapter(_chapter("<html><body><h1>Title</h1><p>body</p></body></html>"))
    assert "Title" in text.plain
    assert "body" in text.plain
