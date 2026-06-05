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
bookreader path/to/book.epub          # open a single book
bookreader                            # (Phase 2) launch library
```

## Keys

| Key         | Action                  |
|-------------|-------------------------|
| `j` / `k`   | Scroll line down / up   |
| `space` / `b` | Page down / up        |
| `n` / `p`   | Next / prev chapter     |
| `t`         | Toggle TOC sidebar      |
| `g` / `G`   | Top / bottom of chapter |
| `T`         | Cycle theme             |
| `q`         | Quit                    |

## Project layout

```
src/bookreader/
  core/   # config, paths, logging, exceptions
  epub/   # parsing + rendering (no UI)
  ui/     # Textual app, screens, widgets
  library/# (Phase 2) persistence + collections
```

## Status

Phase 1 — Reader Core. See `docs/adr/0001-stack-choice.md` and the plan at
`~/.claude/plans/moonlit-popping-sunset.md`.
