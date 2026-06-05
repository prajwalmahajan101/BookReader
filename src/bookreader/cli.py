"""Command-line entrypoint.

Phase 1: ``bookreader <path.epub>`` opens a book in the reader. Phase 2 adds
subcommands for library management.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from bookreader import __version__
from bookreader.core.exceptions import BookReaderError
from bookreader.core.logging import get_logger
from bookreader.epub.reader import open_book
from bookreader.state.positions import PositionStore
from bookreader.ui.app import BookReaderApp

log = get_logger(__name__)


@click.command()
@click.argument(
    "book",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.version_option(__version__, prog_name="bookreader")
def main(book: Path) -> None:
    """Open BOOK (an .epub file) in the terminal reader."""
    try:
        opened = open_book(book)
    except BookReaderError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(2)

    app = BookReaderApp(book=opened, positions=PositionStore())
    app.run()


if __name__ == "__main__":  # pragma: no cover
    main()
