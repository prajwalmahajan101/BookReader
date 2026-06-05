# BookReader

A terminal EPUB reader and personal library, built with [Textual](https://textual.textualize.io/).

## Install (development)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Run

```bash
bookreader                            # library home
bookreader open path/to/book.epub     # open a single book (adds it to the library)
bookreader path/to/book.epub          # same as 'open'
bookreader --no-library <path>        # stateless reader (no library writes)

bookreader add path/to/book.epub      # add without opening
bookreader list                       # print every book in the library
```

## Keys — reader

| Key           | Action                  |
|---------------|-------------------------|
| `j` / `k`     | Scroll line down / up   |
| `space` / `b` | Page down / up          |
| `n` / `p`     | Next / prev chapter     |
| `t`           | Toggle TOC sidebar      |
| `2`           | Toggle two-page mode    |
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

## Status

Phase 1 (Reader Core) + Phase 1.5 (Two-page mode) + Phase 2 (Library)
all live. ADRs at `docs/adr/`. Plan at
`~/.claude/plans/moonlit-popping-sunset.md`.
