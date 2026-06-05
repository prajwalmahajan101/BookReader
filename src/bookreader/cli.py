"""Command-line entry points.

Subcommands:

- ``bookreader open <path>`` — open a single book (alias: ``bookreader <path>``).
- ``bookreader add <path>`` — add a book to the library without opening.
- ``bookreader list`` — print every book in the library.
- ``bookreader`` — launch the library home screen.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from bookreader import __version__
from bookreader.core.exceptions import BookReaderError
from bookreader.core.logging import get_logger
from bookreader.epub.reader import open_book
from bookreader.library import LibraryService
from bookreader.state.positions import PositionStore
from bookreader.ui.app import BookReaderApp

log = get_logger(__name__)


@click.group(invoke_without_command=True)
@click.option(
    "--no-library",
    is_flag=True,
    help="Skip the library DB entirely. Reader becomes stateless beyond positions.json.",
)
@click.version_option(__version__, prog_name="bookreader")
@click.pass_context
def main(ctx: click.Context, *, no_library: bool) -> None:
    """BookReader — terminal EPUB reader and library.

    With no subcommand, launches the library home screen. Use
    ``bookreader open <path>`` to jump straight to the reader.
    """
    ctx.ensure_object(dict)
    ctx.obj["no_library"] = no_library
    if ctx.invoked_subcommand is not None:
        return

    if no_library:
        click.echo("nothing to do: pass a subcommand or run without --no-library", err=True)
        sys.exit(2)

    service = LibraryService()
    try:
        app = BookReaderApp(library=service)
        app.run()
    finally:
        service.close()


@main.command("open")
@click.argument("book", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--no-library", is_flag=True, help="Skip the library DB.")
def open_cmd(book: Path, *, no_library: bool) -> None:
    """Open BOOK (an .epub) in the terminal reader."""
    try:
        parsed = open_book(book)
    except BookReaderError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(2)

    service: LibraryService | None = None
    library_book_id: int | None = None
    if not no_library:
        service = LibraryService()
        try:
            lib_book = service.add_book(book)
            service.touch_opened(lib_book.id)
            library_book_id = lib_book.id
        except BookReaderError as exc:
            click.echo(f"warning: library add failed ({exc})", err=True)

    try:
        app = BookReaderApp(
            book=parsed,
            positions=PositionStore(),
            library=service,
            library_book_id=library_book_id,
        )
        app.run()
    finally:
        if service is not None:
            service.close()


@main.command("add")
@click.argument("book", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def add_cmd(book: Path) -> None:
    """Add BOOK to the library without opening it."""
    service = LibraryService()
    try:
        try:
            lib_book = service.add_book(book)
        except BookReaderError as exc:
            click.echo(f"error: {exc}", err=True)
            sys.exit(2)
        click.echo(f"added: {lib_book.title} [{lib_book.identifier}]")
    finally:
        service.close()


@main.command("list")
def list_cmd() -> None:
    """Print every book in the library."""
    service = LibraryService()
    try:
        books = service.list_books()
        if not books:
            click.echo("(library is empty)")
            return
        for b in books:
            mark = "✓" if b.completed_at else " "
            rating = f"★{b.rating}" if b.rating else "  "
            authors = ", ".join(b.authors) or "—"
            click.echo(f"{mark} {rating}  {b.title}  —  {authors}")
    finally:
        service.close()


_SUBCOMMANDS = {"open", "add", "list"}


def _rewrite_path_sugar(argv: list[str]) -> list[str]:
    """If the user typed ``bookreader some/path.epub``, prepend ``open``.

    Preserves the Phase-1 invocation without confusing Click's subcommand
    dispatch.
    """
    if len(argv) < 2:
        return argv
    first = argv[1]
    if first.startswith("-"):
        return argv
    if first in _SUBCOMMANDS:
        return argv
    if first.endswith(".epub") or "/" in first:
        return [argv[0], "open", *argv[1:]]
    return argv


def entrypoint() -> None:
    """Console-script wrapper that applies the Phase-1 path sugar."""
    sys.argv = _rewrite_path_sugar(sys.argv)
    main()


if __name__ == "__main__":  # pragma: no cover
    entrypoint()
