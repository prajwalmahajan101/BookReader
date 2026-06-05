# ADR 0003 — Migrate to Textual's theme system

Status: Accepted (2026-06-05)

## Context

Phase 1 shipped a homegrown theme system: three CSS classes on the root
`App` element (`.-theme-dark`, `.-theme-light`, `.-theme-sepia`), each
with a wall of selectors mapping concrete hex codes to widgets. `T` cycled
between them by toggling the classes.

Three problems showed up on a real EPUB:

1. **Built-in widgets stayed dark in light/sepia.** Textual's `Header`,
   `Footer`, command-palette indicator, notifications, and scrollbars
   draw against `App.theme` (a first-class theme system added in newer
   Textual). They had no idea about our CSS classes, so footer key hints
   rendered magenta-on-cream and the "^p palette" hint became unreadable.
2. **`T` and the command palette diverged.** Pressing `T` mutated our
   classes; the palette's "Theme" entry mutated `App.theme`. The two
   sources of truth drifted instantly.
3. **Per-theme TCSS blocks are unmaintainable.** Adding one new widget
   meant duplicating its colour rules three times.

## Decision

Migrate fully to Textual's `App.register_theme()` API.

- Register three custom themes named `bookreader-dark`,
  `bookreader-light`, `bookreader-sepia` in `BookReaderApp.on_mount`. Each
  supplies the semantic slots Textual needs: `primary`, `accent`,
  `foreground`, `background`, `surface`, `panel`, `boost`, `warning`,
  `error`, `success`, `dark` (boolean).
- `BookReaderApp.action_cycle_theme` rotates `self.theme` between the
  three names. The command palette's Theme picker mutates the same
  `self.theme`, so both UIs share state.
- `styles.tcss` references theme variables (`$foreground`, `$panel`,
  `$boost`, `$accent`, `$foreground-muted`) instead of hex codes. Per-
  theme blocks deleted entirely.
- `StatusBar` renders progress text with Textual content markup
  (`[$accent]…[/]`) so the progress bar colour follows the theme.

## Consequences

**Positive**
- Built-in widgets (Header, Footer, palette indicator, notifications,
  scrollbars) auto-theme in light and sepia.
- Single source of truth for theme state.
- Adding a new theme = one `Theme(...)` constructor call, no TCSS work.
- TCSS gets noticeably shorter and easier to read.

**Negative**
- `Settings.theme` still uses the short names (`dark`/`light`/`sepia`)
  for ergonomics; the app maps short→registered id in one place
  (`_theme_id`). One extra hop, but it isolates the change.
- Tests don't currently probe theme colours. We rely on pilot smoke
  tests and manual verification.

## Usage

- New theme → add another `Theme(...)` in `_build_themes()` and append
  its short name to `_THEME_ORDER`.
- New TCSS rule → reference `$primary`, `$accent`, `$foreground`,
  `$foreground-muted`, `$panel`, `$boost` etc. Avoid hex codes outside
  the registered theme objects.
- Need a theme variable not in Textual's default set → use the
  `variables={...}` kwarg on `Theme(...)`.
