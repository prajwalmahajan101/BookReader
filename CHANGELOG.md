# Changelog

All notable changes to BookReader are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-06-10

Stable 1.0. Same code surface as 0.4.0 — this release ships the polish
pass that grew up around the project after the first PyPI upload.

### Added
- **README rewrite** geared at first-time users — `pipx` / `uv tool` /
  `pip-in-venv` install paths with a PEP 668 note, terminal × graphics-
  protocol compatibility matrix, Quick Start, Troubleshooting, and a
  `Why bookreader-tui?` comparison vs Calibre / `epy` / `mdcat`.
- **mkdocs-material documentation site** at
  https://prajwalmahajan101.github.io/BookReader/ — auto-deployed on
  every push to `main` that touches `docs/site/`, `mkdocs.yml`, or the
  README/CHANGELOG.
- **Real screenshots** — library, scroll-mode reader, and two-page
  reader captured via a Textual SVG pilot
  (`scripts/capture_screenshots.py`); embedded in the README, PyPI
  long-description, and the docs site.
- **`SECURITY.md`** — vulnerability-reporting policy via GitHub Private
  Vulnerability Reporting.
- **`CONTRIBUTING.md`** — distilled commit / branching / architectural
  conventions for outside contributors.
- **`docs/demo.tape`** — vhs script for an animated README hero. Render
  with `vhs docs/demo.tape` (requires `vhs`/`ffmpeg`/`ttyd`).
- **GitHub repo metadata** — description, homepage URL, and topics
  (`tui`, `textual`, `epub`, `kitty`, `sixel`, …) so the project shows
  up in topical searches.

### Changed
- Project name remains `bookreader-tui` on PyPI; import path remains
  `bookreader`. License remains Apache-2.0.

## [0.4.0] — 2026-06-10

First PyPI release as `bookreader-tui`. Bundles every change from
the post-0.3.0 cleanup waves plus the Phase 4 / 5.0 polish work.

### Added
- **Phase 4 — Library curation.** `C` opens a *Collections* overview
  (every book grouped by collection); `W` opens a *Wishlist* overview
  with in-place removal via `d`.
- **Reader-side library actions.** `c` toggles completion, `C` and `W`
  push the collection / wishlist overviews from inside the reader —
  no more "quit to library first" round-trip.
- **Inline images in two-page mode.** `PagedView` was rewritten from
  Static-render to widget-mount: each spread is `Horizontal[Vertical,
  Vertical]` with mounted `Static` + `Image` widgets per page. Images
  render at natural EPUB size with `width: auto; max-width: 100%`.
- **Auto-enable inline images** in graphics-capable terminals
  (`xterm-kitty`, iTerm2, WezTerm). Explicit `BOOKREADER_IMAGES_ENABLED`
  still wins. New `I` key toggles at runtime.
- **Configurable reading width.** `BOOKREADER_READING_WIDTH` (60–200)
  overrides the column max. Default raised 84 → 110.
- **Library UX polish.** Empty-state hints when a filter has 0 books;
  filter-aware status strip (`showing 0 of 1 · filter: Want to Read`);
  sidebar + table get accent-coloured focus borders; book table has
  explicit column widths.
- **RepositoryError** at the SQLite boundary so UI code can route
  through the central `BookReaderError` handler.
- **Lowercase `w` hint** on the library — instead of silently doing
  nothing, surfaces "Press Shift+W to open the wishlist".
- **Dark theme contrast** — Tokyo-Night-adjacent palette replaces the
  muted Catppuccin Mocha values (brighter foreground, punchier accent).
- **`Ctrl+P` theme picker scoped to bookreader-\*** — the 20+ Textual
  built-in themes no longer pollute the picker.
- **CI on every push / PR** — ruff format + check, mypy --strict,
  pytest across Python 3.11 and 3.12.

### Fixed
- Bare `except Exception` in UI handlers replaced with
  `except BookReaderError`; programming bugs (KeyError, AttributeError)
  no longer get silently rendered as "Add failed" notifications.
- `q` typed inside a modal `Input` can no longer quit the app
  (verified with a pilot regression test).
- `T` theme cycle now snaps back to the bookreader theme set after the
  user picks a Textual built-in via the palette.
- Inline `Image` widget no longer eats all vertical space — explicit
  `height: auto` keeps the text below the figure visible.
- `PagedView` re-renders use class selectors instead of static IDs;
  the async `remove_children()` race no longer raises `DuplicateIds`
  on resize / chapter jump (regression test added).

### Changed
- Versioning: `__version__` and `pyproject.toml` bumped 0.1.0 → 0.4.0
  (matches the actual shipped surface — Phase 4 was on `main` long
  before the version field caught up).
- PyPI package name: `bookreader-tui` (the bare `bookreader` name was
  already taken). The Python import path is still `bookreader`.
- License declaration in `pyproject.toml` corrected from `MIT` to
  `Apache-2.0` to match the actual LICENSE file.

## [0.3.0] — 2026-04-05

Phase 3 — Polish.

### Added
- **Phantom (wishlist) books.** Add a TBR entry by title + author with
  no file (`bookreader add --wishlist --title "T" --author "A"`);
  promote with `bookreader attach <id> path.epub`.
- **Bookmarks.** `m` adds a bookmark with optional note; `'` lists
  bookmarks for the current book, Enter jumps.
- **Reading-session stats.** Per-book minutes-read accrue
  automatically; `bookreader stats` prints totals; library "Time"
  column shows running totals.
- **Inline images.** `BOOKREADER_IMAGES_ENABLED=1` enables kitty /
  iTerm / sixel rendering via `textual-image`; otherwise figures fall
  back to `[image: alt]` placeholders.
- ADR-0004 records the Phase 3 data-model decisions.

## [0.2.2] — 2026-03-15

### Fixed
- Two-page reading column widened from 84 → 140 cells so each page
  carries ~68 cells of prose instead of the squeezed ~40 each.

## [0.2.1] — 2026-03-12

### Added / Changed
- Migrated to Textual's first-class theme system (`App.register_theme`)
  so the command palette, header, footer, and notifications all adapt
  with the bookreader themes. ADR-0003 records the migration.

### Fixed
- Two-column pagination produced visibly unequal column widths because
  the math ignored Rich's grid padding. Now stitches columns
  line-by-line with exact widths.

## [0.2.0] — 2026-03-05

Phase 2 — Library.

### Added
- SQLite library with `books`, `collections`, `bookmarks`, `positions`,
  and `book_collections` tables. Hand-rolled migrations under
  `library/migrations/`.
- `bookreader` (no args) lands on the library home screen. `bookreader
  open <path>` keeps the Phase-1 reader flow.
- CLI subcommands: `add`, `list`.
- `LibraryService` mediates between UI and repositories. Position
  saves mirror through the service to the DB.
- One-shot migration: Phase-1 `positions.json` entries that match
  books in the library are imported, then the JSON is renamed.
- ADR-0002 records the Phase 2 schema and layering decisions.

## [0.1.1] — 2026-02-22

### Added
- Two-page reading mode toggled with `2`. Wraps the chapter into two
  side-by-side columns; `space` / `b` advance one spread.

## [0.1.0] — 2026-02-15

Initial release. Phase 1 — Reader Core.

### Added
- EPUB parsing + chapter iteration via `ebooklib` + `beautifulsoup4`.
- Textual reader screen: TOC sidebar, centered ≤ 84-cell reading
  column, status bar with chapter progress.
- Keyboard navigation: `j`/`k` scroll, `space`/`b` page, `n`/`p`
  chapter, `t` TOC, `g`/`G` top/bottom, `T` theme, `?` help, `q` quit.
- Auto-flow into next/prev chapter at boundaries.
- Three themes (dark, light, sepia) with focus-tinted borders.
- Position persistence keyed by EPUB `dc:identifier` (JSON store).
- 12 unit tests; ruff clean; mypy strict.
- ADR-0001 records the stack choice (Textual + ebooklib + SQLite).

[1.0.0]: https://github.com/prajwalmahajan101/BookReader/releases/tag/v1.0.0
[0.4.0]: https://github.com/prajwalmahajan101/BookReader/releases/tag/v0.4.0
[0.3.0]: https://github.com/prajwalmahajan101/BookReader/releases/tag/v0.3.0
[0.2.2]: https://github.com/prajwalmahajan101/BookReader/releases/tag/v0.2.2
[0.2.1]: https://github.com/prajwalmahajan101/BookReader/releases/tag/v0.2.1
[0.2.0]: https://github.com/prajwalmahajan101/BookReader/releases/tag/v0.2.0
[0.1.1]: https://github.com/prajwalmahajan101/BookReader/releases/tag/v0.1.1
[0.1.0]: https://github.com/prajwalmahajan101/BookReader/releases/tag/v0.1.0
