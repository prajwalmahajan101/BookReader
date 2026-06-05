# ADR 0001 — Stack Choice

Status: Accepted (2026-06-05)

## Context

BookReader is a terminal EPUB reader with a personal-library layer
(collections, ratings, completion). It needs:

- A TUI framework that handles layout, scrolling, theming, async input.
- An EPUB parser that handles EPUB 2 and 3 without writing zip + XML glue.
- A storage layer for books, collections, positions, bookmarks, ratings.
- Inline image rendering on terminals that support kitty / sixel graphics,
  with a clean fallback.

The codebase follows the conventions of `colending_partner`
(async-first, src layout, ruff + mypy + pytest, pydantic, atomic commits).

## Decision

| Concern        | Choice                                                |
|----------------|-------------------------------------------------------|
| TUI framework  | **Textual** — async-native, CSS theming, mature.       |
| EPUB parsing   | **ebooklib + beautifulsoup4 + lxml**.                  |
| Image render   | **term-image** (Phase 3) — auto-detects kitty / sixel. |
| Storage        | **SQLite via stdlib `sqlite3`** (Phase 2+).            |
| Config         | **pydantic-settings**.                                 |
| CLI            | **click**.                                             |
| Paths          | **platformdirs** (XDG-correct).                        |

Phase 1 ships a single-file reader with JSON position persistence; SQLite
arrives in Phase 2 when the library layer lands.

## Consequences

**Positive**

- Textual gives async, theming, and resize handling for free — matches the
  house async style.
- ebooklib hides the EPUB zip + OPF + NCX details.
- SQLite (stdlib) means zero ORM overhead and no extra dependency.
- term-image keeps image support optional and degrades gracefully.

**Negative / risks**

- Textual is moving fast; pin a known-good version.
- ebooklib's API is dated — wrap it behind `epub.reader` so we can replace it.
- No ORM means we hand-roll migrations. We accept this; the schema is small.

## Usage

- New persistence touching books / collections / positions goes through
  `library.repository`, not raw `sqlite3` from the UI.
- New EPUB-shaped code goes through `epub.reader` so the parser stays
  swappable.
- Adding a TUI screen → subclass `textual.screen.Screen`, register on
  `ui.app.BookReaderApp`.
