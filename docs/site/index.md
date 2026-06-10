# bookreader-tui

A terminal EPUB reader and personal library, built with
[Textual](https://textual.textualize.io/).

```bash
pipx install bookreader-tui && bookreader path/to/book.epub
```

![library](https://raw.githubusercontent.com/prajwalmahajan101/BookReader/main/docs/screenshots/library.svg)

## What you get

- Distraction-free reader, scroll or two-page mode, TOC sidebar.
- Persistent position per book — picks up exactly where you left off.
- SQLite library with collections, ratings, bookmarks, reading-time stats.
- Wishlist (phantom) books — track titles before you have the file.
- Inline image rendering in `kitty` / `iTerm2` / `WezTerm` / sixel terminals via
  [textual-image](https://pypi.org/project/textual-image/) — auto-detected.
- Three built-in themes (`dark`, `light`, `sepia`).
- Pure Python, fully local — your library lives in `~/.local/share/bookreader/`.

## Why bookreader-tui?

- **vs Calibre** — no Qt, no GUI process; lives where the rest of your
  terminal workflow already is.
- **vs `epy`** — full library: collections, ratings, wishlist, reading-time
  stats, bookmarks with notes.
- **vs `mdcat` / piping to a pager** — proper EPUB rendering (chapters, TOC,
  two-page mode, inline images), not a flat text dump.
- **vs reading on your phone** — keyboard-driven, themed, scriptable;
  position keyed by EPUB identifier so the same book at a different path
  resumes in the same place.

## Get going

- [Install](install.md) — pipx, uv tool, or pip-in-venv.
- [Quick start](quickstart.md) — open your first book in 30 seconds.
- [Terminal images](images.md) — compatibility matrix + setup.
- [Configuration](configuration.md) — env vars and XDG paths.
- [Troubleshooting](troubleshooting.md) — common fixes.
