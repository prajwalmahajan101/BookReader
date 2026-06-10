# Troubleshooting

## `bookreader: command not found`

You installed with `pip install bookreader-tui` directly into your system
Python and PEP 668 blocked it, or you installed into a venv that isn't
activated.

```bash
pipx install bookreader-tui          # recommended
# OR:
source .venv/bin/activate            # if you used a venv
```

## Images render as `[image: alt]` placeholders even in kitty

Check the env var:

```bash
echo "$BOOKREADER_IMAGES_ENABLED"
```

If it's `0`, unset it or set to `1`. Inside the reader, press `I` to
force-toggle. If it still doesn't render, your kitty session may be inside
`tmux` / `screen` without graphics passthrough — start kitty directly to
confirm.

## Images render at low quality

The image is being upscaled into a column that's too narrow. Raise the
reading width:

```bash
BOOKREADER_READING_WIDTH=160 bookreader path/to/book.epub
```

The image renders at its natural pixel size, capped at the column width;
wider column → more cells available → sharper rendering in kitty.

## `q` quits while I'm typing in a wishlist title

It shouldn't — modals isolate keystrokes. If you hit this, please open an
issue with your terminal + Textual version:
[github.com/prajwalmahajan101/BookReader/issues](https://github.com/prajwalmahajan101/BookReader/issues/new).

## My EPUB has no images at all

Confirm with the parser directly:

```bash
python - <<'PY'
from ebooklib import epub
b = epub.read_epub("path/to/book.epub")
n = sum(1 for i in b.get_items() if i.media_type.startswith("image/"))
print(f"image items in EPUB: {n}")
PY
```

If that prints `0`, the EPUB itself has no embedded images.

## Library got corrupted

Stop the app. Move the file aside and re-launch:

```bash
mv ~/.local/share/bookreader/library.db{,.bak}
bookreader
```

A fresh library is created. Repopulate with `bookreader add <path>`.

## I want a clean slate

```bash
rm -rf ~/.local/share/bookreader ~/.local/state/bookreader
```

Removes the library, positions, bookmarks, and logs.

## CI / build issues (from source)

```bash
# Re-install dev deps after a new commit added a runtime dep
pip install -e ".[dev]"

# Run the full gate locally
pytest -q
ruff format --check . && ruff check src/ tests/
mypy src/
```

If pytest fails on first run after a pull, check
`tests/integration/test_paged_view_rerender.py` first — async re-render
regressions show up there.

## Reporting bugs

Open a GitHub issue:
[github.com/prajwalmahajan101/BookReader/issues](https://github.com/prajwalmahajan101/BookReader/issues/new).
Include:

- Output of `bookreader --version`
- Terminal emulator + version
- Python version (`python --version`)
- The minimum-reproducing EPUB (or its identifier if you can't share)
- Relevant lines from `~/.local/state/bookreader/log/bookreader.log`
