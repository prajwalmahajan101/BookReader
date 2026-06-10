# BookReader

[![PyPI](https://img.shields.io/pypi/v/bookreader-tui.svg)](https://pypi.org/project/bookreader-tui/)
[![Python](https://img.shields.io/pypi/pyversions/bookreader-tui.svg)](https://pypi.org/project/bookreader-tui/)
[![License](https://img.shields.io/pypi/l/bookreader-tui.svg)](./LICENSE)
[![test](https://github.com/prajwalmahajan101/BookReader/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/prajwalmahajan101/BookReader/actions/workflows/test.yml)

> A terminal EPUB reader and personal library, built with [Textual](https://textual.textualize.io/) — for people who'd rather read in their terminal than launch a desktop app.

![BookReader theme picker](https://raw.githubusercontent.com/prajwalmahajan101/BookReader/main/docs/screenshots/theme-picker.png)

BookReader opens any EPUB in a focused two-column or two-page TUI, remembers where you left off, indexes everything you've added into a small SQLite library, and tracks per-book reading time and bookmarks. Inline `kitty` / `iTerm2` / `sixel` image rendering is auto-enabled when your terminal advertises a graphics protocol; otherwise figures fall back to `[image: alt]` placeholders.

Built solo as a phase-driven exercise: each phase is a feature branch with its own ADR, atomic commits, and merge-clean history. Currently shipped: **Phase 1 (Reader Core)**, **Phase 1.5 (Two-page mode)**, **Phase 2 (SQLite Library)**, **Phase 3 (Polish — bookmarks, sessions, phantom / wishlist books, inline images)**, **Phase 4 (Library curation — collections + wishlist overview)**.

## How it's built

- **Layered architecture** — `core` (config/paths/logging, no I/O) · `epub` (parse + render, no UI/DB) · `library` (persistence + service) · `ui` (Textual screens + widgets). The UI never imports a repository directly; it goes through a service. Decisions live in [`docs/adr/`](./docs/adr/).
- **Strict typing + linting** — mypy strict, ruff (format + lint), pre-commit enforced. PEP 257 + Google docstrings; module-level logger via `bookreader.core.logging.get_logger(__name__)`.
- **Dependencies** — `pip-tools` with layered `requirements/*.in → *.txt` (runtime / dev / test split).
- **Async-first** — `pytest-asyncio` with `asyncio_mode = auto`.
- **Commit discipline** — conventional commits, atomic, on `feature/phaseN_<topic>` branches; `main` is always releasable. History stays linear: each phase is its own feature branch, fast-forward-merged into main with atomic conventional commits.

## Install

From PyPI:

```bash
pip install bookreader-tui
bookreader path/to/book.epub
```

The PyPI package name is `bookreader-tui` (the bare `bookreader` was
taken); the import path and the console script are still `bookreader`.

### Development install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

> If you pulled new commits that added runtime dependencies (e.g.
> `textual-image`), re-run `pip install -e ".[dev]"` inside the
> activated venv so the editable install refreshes its metadata.

## Run

```bash
bookreader                            # library home
bookreader open path/to/book.epub     # open a single book (adds it to the library)
bookreader path/to/book.epub          # same as 'open'
bookreader --no-library <path>        # stateless reader (no library writes)

bookreader add path/to/book.epub      # add without opening
bookreader add --wishlist --title "T" --author "A"   # wishlist (TBR) entry, no file
bookreader attach <book-id> path.epub # promote a wishlist row to a real book
bookreader list                       # print every book in the library
bookreader stats                      # minutes read per book
```

## Keys — reader

| Key           | Action                  |
|---------------|-------------------------|
| `j` / `k`     | Scroll line down / up   |
| `space` / `b` | Page down / up          |
| `n` / `p`     | Next / prev chapter     |
| `t`           | Toggle TOC sidebar      |
| `2`           | Toggle two-page mode    |
| `m`           | Add a bookmark (with optional note) |
| `'`           | List bookmarks — Enter jumps |
| `c`           | Toggle completion of the current book |
| `C` (shift+c) | Open Collections overview from inside the reader |
| `W` (shift+w) | Open Wishlist overview from inside the reader |
| `I` (shift+i) | Toggle inline image rendering at runtime |
| `g` / `G`     | Top / bottom of chapter |
| `T`           | Cycle theme (dark/light/sepia) |
| `?`           | Show key hints          |
| `q`           | Save and back (or quit) |

Scrolling past the end of a chapter flows into the next one automatically;
going back from the start flows into the previous chapter's end.

## Keys — library

| Key                | Action                                |
|--------------------|---------------------------------------|
| Enter / `i`        | Open the highlighted book             |
| `a`                | Add a book (prompts for path)         |
| `A` (shift+a)      | Add a wishlist entry (title + author) |
| `C` (shift+c)      | Browse all books grouped by collection (title + path) |
| `W` (shift+w)      | Browse wishlist (title + author); `d` removes |
| `d` / Delete       | Remove the highlighted book           |
| `c`                | Toggle completion                     |
| `1` … `5`          | Set rating; `0` clears                |
| Tab                | Switch focus between sidebar & table  |
| `T` / `?` / `q`    | Theme / help / quit                   |

## Project layout

```
src/bookreader/
  core/      # config, paths, logging, exceptions
  epub/      # parsing + rendering (no UI)
  state/     # Phase-1 JSON position store
  library/   # SQLite library (Phase 2): db, repo, service, migrations
  ui/        # Textual app, screens, widgets, themes
```

## Storage

| What                       | Where                                      |
|----------------------------|--------------------------------------------|
| Library DB                 | `<XDG_DATA_HOME>/bookreader/library.db`    |
| Phase-1 positions JSON     | `<XDG_STATE_HOME>/bookreader/positions.json` |
| Log file (rotating)        | `<XDG_STATE_HOME>/bookreader/log/bookreader.log` |

Upgrading from Phase 1: on first launch the library service migrates
`positions.json` entries that match books already added; the JSON is
renamed to `positions.json.migrated` once data flows.

## Environment overrides

| Variable                       | Effect                                                       |
|--------------------------------|--------------------------------------------------------------|
| `BOOKREADER_IMAGES_ENABLED`    | `1` forces inline images on; `0` forces off. Defaults to auto-detect in kitty / iTerm2 / WezTerm. |
| `BOOKREADER_READING_WIDTH`     | Single-column reading width in cells (60–200, default 110).  |
| `BOOKREADER_THEME`             | `dark`, `light`, `sepia`.                                    |
| `BOOKREADER_TWO_PAGE_DEFAULT`  | `1` to start in two-page mode.                               |
| `NO_COLOR`                     | Honoured by `textual` — falls back to safe color set.        |

## Status

Phase 1 (Reader Core) + Phase 1.5 (Two-page mode) + Phase 2 (Library) +
Phase 3 (Polish — bookmarks, sessions, phantom books, inline images) +
Phase 4 (Library Curation — collections + wishlist overview screens)
all live. ADRs at `docs/adr/`.

### Phase 4 highlights

- `C` on the library opens a **Collections** overview screen — every book
  grouped by collection, title + path per row.
- `W` opens a **Wishlist** overview — every phantom (TBR) entry as
  title + author; `d` removes.
- Both screens are integration-tested (`tests/integration/test_library_modals.py`).

### Phase 3 highlights

- `bookreader add --wishlist --title …` tracks TBR titles before you
  have the EPUB; `bookreader attach <id> path.epub` promotes them.
- `m` / `'` add and list per-book bookmarks (with optional notes).
- Reading time per book accrues automatically; see it in the library
  "Time" column or via `bookreader stats`.
- Inline kitty/sixel images render when `BOOKREADER_IMAGES_ENABLED=1`
  is set and the terminal supports a graphics protocol. Otherwise a
  `[image: alt]` placeholder takes the figure's place. Paged mode
  (`2`) always uses the placeholder.

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for the version-by-version history.

## License

[Apache-2.0](./LICENSE) — Copyright 2026 Prajwal Mahajan.
