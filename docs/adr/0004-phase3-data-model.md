# ADR 0004 — Phase 3 data model (phantom books, sessions, image blocks)

Status: Accepted (2026-06-05)

## Context

Phase 3 added four features. Three of them changed the data model:

1. **Phantom books** — track wishlist titles before the EPUB is in hand.
2. **Reading sessions** — tally minutes per book.
3. **Image blocks** — split chapter rendering into text and image runs.

(Bookmarks already had a schema from Phase 2; only the UI was new.)

## Decision

### Schema

- **Migration `0002_phantom_books.sql`** — table rebuild that relaxes
  ``books.file_path`` to nullable and adds ``is_phantom INTEGER NOT NULL
  DEFAULT 0`` plus a CHECK that forbids real rows with no file. Phantom
  rows use ``identifier = "phantom:<uuid4>"`` so the ``UNIQUE`` index
  still holds.
- **Migration `0003_sessions.sql`** — append-only ``sessions`` table
  with ``book_id`` FK, ``started_at``, optional ``ended_at``,
  ``pages_advanced``. Index on ``(book_id, started_at DESC)``.

### Service contract

- ``LibraryService.add_wishlist(title, authors)`` inserts a phantom row
  and (by default) joins it to the seeded ``Want to Read`` collection.
- ``LibraryService.attach_epub(book_id, path)`` promotes a phantom into
  a real book by parsing the EPUB and updating identifier / file_path
  in place. Collection membership and ratings survive.
- ``LibraryService.start_session(book_id)`` returns a Session;
  ``end_session(session_id, pages_advanced=…)`` is idempotent. Defensive
  ``close_orphans()`` runs on service construction so a crashed run
  doesn't keep "now − started_at" inflating stats forever.

### Rendering

- ``epub.renderer.render_chapter_blocks(chapter, book)`` returns a list
  of ``TextBlock | ImageBlock``. Image hrefs are resolved against the
  chapter's directory and looked up in the new ``Book.images`` map.
- ``render_chapter(chapter)`` stays — it emits ``[image: alt]`` text
  placeholders. That preserves the contract :class:`PagedView` depends
  on, since wrapping image widgets between two columns is undefined.
- ``ChapterView`` becomes a ``Vertical`` container that mounts a Static
  per ``TextBlock`` and an image widget (gated on
  ``Settings.images_enabled``) per ``ImageBlock``.

## Consequences

**Positive**

- Wishlist entries live in the same shape as real books — collections,
  ratings, completion, even position rows all work the same. One row,
  one identifier, one path through the UI.
- Sessions are minimal but composable: per-book totals, last-read date,
  and "pages advanced" all compute from the same table.
- PagedView is untouched. Risk surface stays small.
- The image widget gracefully degrades to a placeholder Static when
  ``textual_image`` or ``PIL`` aren't usable in the active terminal.

**Negative / risks**

- The ``books`` table rebuild is the first non-additive migration. We
  use SQLite's CREATE-INSERT-DROP-RENAME idiom; the migration is fast
  on libraries of any realistic size.
- ``Book.images`` is held in memory for the life of the book. Phase 4
  could move to lazy loading via ``LibraryService`` if a 200 MB EPUB
  ever arrives, but for now it isn't worth the complexity.

## Usage

- New CLI subcommand that needs the library → add as `@main.command`
  in `cli.py`, mirror the `add` / `attach` / `stats` shape.
- New screen that needs images → load with ``render_chapter_blocks`` and
  the parent ``Book`` so figures resolve.
- New session-aware widget → call ``LibraryService.sessions.last_session_for``
  or ``minutes_read``. Do not touch the connection directly.
