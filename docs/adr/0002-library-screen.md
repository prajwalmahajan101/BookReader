# ADR 0002 — Library Screen + Routing

Status: Accepted (2026-06-05)

## Context

Phase 2 added a SQLite-backed library: books, collections, ratings, and
completion. The next question was how the existing single-book reader
(Phase 1) should coexist with a library home screen, and how the CLI
should route.

Constraints:

- The Phase-1 invocation `bookreader path.epub` must keep working.
- Quitting the reader after launching from the library must return to the
  library, not the shell.
- The reader must keep working without a library (offline / one-shot mode).
- The same `dc:identifier` must address a book whether opened by path or
  from the library — no duplication.

## Decision

**Routing — `ui.app.BookReaderApp`:**

| Invocation                       | Entry screen   | Library write-through |
|----------------------------------|----------------|-----------------------|
| `bookreader`                     | `LibraryScreen`| yes                   |
| `bookreader open <path>`         | `ReaderScreen` | yes (add + touch)     |
| `bookreader <path>`              | `ReaderScreen` | yes (sugar for `open`)|
| `bookreader --no-library <path>` | `ReaderScreen` | no                    |
| `bookreader add <path>`          | (no UI)        | yes                   |
| `bookreader list`                | (no UI)        | yes                   |

**Position write-through:** `ReaderScreen._save_position` always writes
the Phase-1 JSON store; when a `LibraryService` is attached it *also*
writes the library `positions` row. Lookup prefers the library DB and
falls back to the JSON file, so users upgrading from Phase 1 don't lose
their place.

**Library screen:** IDE three-panel layout — collection sidebar
(`CollectionList`), `DataTable` of books, status strip + footer. Status
icons (`✓` / `●` / `○`) pair with colour per tui-design rules. Ratings
render as `★★★☆☆ (3)` so they read in monochrome.

**Quit behaviour:** `q` in the reader pops back if the screen stack has
more than one entry; otherwise it exits. The library screen is told to
`reload()` after the pop so counts and `last_opened_at` are fresh.

## Consequences

**Positive**

- Backwards-compatible CLI for users from Phase 1.
- Reader and library share the same `Book.identifier` keying so
  positions, bookmarks, and collections all flow naturally.
- One central error route — `BookReaderApp._handle_exception` still
  catches `BookReaderError` regardless of which screen raised it.
- Tests for the library service don't need to import Textual.

**Negative / risks**

- Two write paths for positions until the JSON store is retired. We accept
  the duplication for now because (a) it's cheap, and (b) it lets the user
  delete the library file and fall back to JSON.
- Modifying private attributes (`_library_book_id`) is acceptable inside
  the app + reader pair because they live in the same package. We don't
  expose it on the Screen public API.

## Usage

- New CLI subcommand → add it as a `@main.command(...)` in `cli.py`.
  Construct a fresh `LibraryService` per command and close it in
  `finally`.
- New library screen action → use `LibraryService` only; don't reach into
  repositories from the UI.
- New ReaderScreen state → pass through `BookReaderApp.__init__` to keep
  construction-from-CLI symmetric with construction-from-library.
