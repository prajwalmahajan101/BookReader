"""Shared test fixtures.

We build a small EPUB on disk in a tmp directory rather than committing a
binary. This keeps the repo lean and avoids licensing questions about
which Project Gutenberg book to ship.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ebooklib import epub


@pytest.fixture(scope="session")
def sample_epub(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a minimal three-chapter EPUB and return its path."""
    book = epub.EpubBook()
    book.set_identifier("urn:test:bookreader:sample-001")
    book.set_title("The Sample Book")
    book.set_language("en")
    book.add_author("Test Author")

    chapters = []
    for i in range(1, 4):
        ch = epub.EpubHtml(
            title=f"Chapter {i}",
            file_name=f"chap_{i}.xhtml",
            lang="en",
        )
        ch.content = (
            f"<html><body>"
            f"<h1>Chapter {i}</h1>"
            f"<p>This is the body of chapter <strong>{i}</strong>.</p>"
            f"<p>A second paragraph with <em>emphasis</em>.</p>"
            f"</body></html>"
        )
        book.add_item(ch)
        chapters.append(ch)

    book.toc = tuple(
        epub.Link(c.file_name, c.title, f"chap_{i + 1}") for i, c in enumerate(chapters)
    )
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *chapters]

    path = tmp_path_factory.mktemp("epub") / "sample.epub"
    epub.write_epub(str(path), book)
    return path
