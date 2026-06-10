"""Generate the README/PyPI hero screenshots as SVG.

Drives the real :class:`BookReaderApp` under Textual's pilot harness,
seeds a small library, and saves three screens to
``docs/screenshots/``:

- ``library.svg``   — library home with a populated table
- ``reader.svg``    — scroll-mode reader on a chapter
- ``reader-paged.svg`` — two-page spread on the same chapter

Run with: ``python scripts/capture_screenshots.py``. No CLI args.

Why SVG: Textual's ``save_screenshot`` emits a self-contained SVG that
renders pixel-perfect on GitHub and PyPI, no external rasterisation
step needed.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from bookreader.epub.reader import open_book
from bookreader.library.database import Database
from bookreader.library.service import LibraryService
from bookreader.state.positions import PositionStore
from bookreader.ui.app import BookReaderApp

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "docs" / "screenshots"
SAMPLE_EPUB = Path("/home/prjawal/Documents/book.epub")

LIBRARY_SIZE = (180, 50)
READER_SIZE = (200, 55)


def _seed(service: LibraryService) -> int:
    """Add the sample EPUB + a handful of wishlist rows; return its id."""
    book = service.add_book(SAMPLE_EPUB)
    service.touch_opened(book.id)
    finished = next(c for c in service.list_collections() if c.name == "Finished")
    service.assign_to_collection(book.id, finished.id)
    service.mark_complete(book.id)
    service.rate(book.id, 4)
    for title, author in [
        ("Project Hail Mary", "Andy Weir"),
        ("Babel", "R.F. Kuang"),
        ("The Three-Body Problem", "Liu Cixin"),
        ("Dune", "Frank Herbert"),
    ]:
        service.add_wishlist(title, [author])
    return book.id


async def _capture_library(service: LibraryService) -> None:
    app = BookReaderApp(library=service)
    async with app.run_test(size=LIBRARY_SIZE) as pilot:
        await pilot.pause()
        await pilot.pause()
        app.save_screenshot(filename="library.svg", path=str(OUT_DIR))


async def _capture_reader(service: LibraryService, book_id: int) -> None:
    parsed = open_book(SAMPLE_EPUB)
    app = BookReaderApp(
        book=parsed,
        positions=PositionStore(),
        library=service,
        library_book_id=book_id,
    )
    async with app.run_test(size=READER_SIZE) as pilot:
        await pilot.pause()
        await pilot.press("n", "n", "n")  # jump a few chapters in
        await pilot.pause()
        app.save_screenshot(filename="reader.svg", path=str(OUT_DIR))
        await pilot.press("2")  # paged mode
        await pilot.pause()
        await pilot.pause()
        app.save_screenshot(filename="reader-paged.svg", path=str(OUT_DIR))


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        service = LibraryService(Database(Path(tmp) / "lib.db"))
        try:
            book_id = _seed(service)
            await _capture_library(service)
            await _capture_reader(service, book_id)
        finally:
            service.close()
    print("Wrote:")
    for path in sorted(OUT_DIR.glob("*.svg")):
        size = path.stat().st_size
        print(f"  {path.relative_to(REPO_ROOT)}  ({size:,} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
