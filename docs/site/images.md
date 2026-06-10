# Terminal images

Inline image rendering is wired through
[textual-image](https://pypi.org/project/textual-image/), which talks the
Kitty Graphics Protocol, the iTerm2 inline-image protocol, and Sixel, with
half-block and Unicode fallbacks for everything else.

On launch, `bookreader` sniffs your terminal and enables images if it
recognises a graphics-capable one. Explicit `BOOKREADER_IMAGES_ENABLED`
always wins over auto-detection.

## What works out of the box

| Terminal       | Protocol used         | Notes                                                  |
|----------------|-----------------------|--------------------------------------------------------|
| **kitty**      | Kitty Graphics (TGP)  | Best fidelity. Detected via `TERM=xterm-kitty` / `KITTY_WINDOW_ID`. |
| **Ghostty**    | Kitty Graphics (TGP)  | Native support; behaves like kitty.                    |
| **iTerm2**     | iTerm2 inline images  | macOS. Detected via `TERM_PROGRAM=iTerm.app`.          |
| **WezTerm**    | Kitty / iTerm / Sixel | Supports all three. Detected via `TERM_PROGRAM=WezTerm`. |
| **Konsole**    | Kitty (partial)       | Recent versions.                                       |
| **VS Code terminal** | iTerm2 inline images | Static images only.                              |

## Sixel terminals (force-enable)

`foot`, `mlterm`, `xterm` (built with `--enable-sixel-graphics`), `mintty`,
`Contour`, and `Windows Terminal` aren't covered by auto-detection. Set
the override:

```bash
BOOKREADER_IMAGES_ENABLED=1 bookreader path/to/book.epub
```

## Terminals without graphics support

Anything else (plain `xterm`, `gnome-terminal`, `Terminal.app`, tmux without
a graphics-capable host) renders figures as `[image: alt]` placeholders.
Text reading is unaffected.

## Toggling at runtime

Press **`I`** inside the reader to flip image rendering on/off mid-session.
Useful when an image breaks layout, or to compare with placeholders.

## Image sizing

Images render at their natural EPUB size, capped at the reading column
width. The single-column max is `BOOKREADER_READING_WIDTH` cells (default
`110`). If images look small, raise it:

```bash
BOOKREADER_READING_WIDTH=160 bookreader path/to/book.epub
```

## Known caveats

- **tmux without graphics passthrough** — your tmux build needs explicit
  passthrough for the terminal's graphics protocol. Without it, your
  outer terminal can't see the escape sequences from inside tmux.
- **Tall sixel images** — `textual-image` notes that tall Sixel images
  in Rich can be displaced; symptom is broken borders. Switch to a TGP
  terminal if you hit it.
- **Two-page mode** — images render in both modes; in paged mode they
  consume roughly 60% of a page when they appear.
