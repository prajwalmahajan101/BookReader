# Configuration

All settings are environment variables prefixed `BOOKREADER_`. Set them in
your shell rc, in a `.env` file in your working directory, or per
invocation.

## Environment variables

| Variable                       | Default       | Effect                                                  |
|--------------------------------|---------------|---------------------------------------------------------|
| `BOOKREADER_IMAGES_ENABLED`    | auto-detect   | `1` to force inline images on; `0` to force off.        |
| `BOOKREADER_READING_WIDTH`     | `110`         | Single-column reading width in cells (60–200).          |
| `BOOKREADER_THEME`             | `dark`        | `dark`, `light`, or `sepia`.                            |
| `BOOKREADER_TWO_PAGE_DEFAULT`  | `0`           | `1` to launch in two-page mode.                         |
| `BOOKREADER_LINE_SCROLL`       | `1`           | Lines per `j`/`k` press (1–10).                         |
| `BOOKREADER_PAGE_SCROLL_PCT`   | `90`          | Page jump as a percentage of viewport (10–100).         |
| `BOOKREADER_SHOW_TOC_DEFAULT`  | `1`           | `0` to start with the TOC sidebar collapsed.            |
| `NO_COLOR`                     | unset         | Honoured by `textual` — falls back to a safe palette.   |

## File locations (XDG)

| What                       | Default path                                         |
|----------------------------|------------------------------------------------------|
| Library DB                 | `~/.local/share/bookreader/library.db`               |
| Reading-position cache     | `~/.local/state/bookreader/positions.json`           |
| JSON bookmark fallback     | `~/.local/state/bookreader/bookmarks.json`           |
| Log file (rotating)        | `~/.local/state/bookreader/log/bookreader.log`       |

Honours `XDG_DATA_HOME` and `XDG_STATE_HOME` if set. Safe to back up the
whole `~/.local/share/bookreader/` directory.

## Upgrading from a 0.x JSON store

On first launch the library service migrates
`~/.local/state/bookreader/positions.json` entries that match books already
added; the JSON is renamed to `positions.json.migrated` once data flows.
No manual step needed.

## Themes

Built-in: `bookreader-dark`, `bookreader-light`, `bookreader-sepia`. Cycle
with `T` inside the reader or library; or open the command palette
(`Ctrl+P`) and select **Theme**. The picker is scoped to bookreader themes
only — the 20+ Textual built-in themes are unregistered at startup.

## Reading position model

Positions are keyed by EPUB `dc:identifier`. The same book opened at a
different path on disk resumes at the same chapter + scroll offset.
