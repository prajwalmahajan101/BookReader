# Quick start

After [installing](install.md):

```bash
# Open a book directly. Gets added to your library on first open.
bookreader path/to/book.epub

# Or land on the library home and pick a book with Enter.
bookreader

# One-off read without touching the library.
bookreader --no-library path/to/book.epub
```

That's it. Position, bookmarks, and reading time persist automatically.

## First five minutes

1. **Open a book.** `bookreader ~/Documents/whatever.epub`
2. **Scroll.** `j` / `k` for one line, `space` / `b` for a page,
   `n` / `p` for the next/previous chapter.
3. **Try the two-page spread.** Press `2` to toggle.
4. **Bookmark something interesting.** Press `m`, type a note, Enter.
5. **Quit and reopen.** Position restores automatically.

## CLI subcommands

```bash
# Add a book without opening
bookreader add path/to/book.epub

# Track a TBR title before you have the file
bookreader add --wishlist --title "Project Hail Mary" --author "Andy Weir"

# Later, attach the EPUB to that wishlist entry
bookreader attach 5 path/to/project-hail-mary.epub

# Inspect your library
bookreader list
bookreader stats           # minutes read per book
bookreader --version
```
