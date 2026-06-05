-- BookReader library schema, version 2.
--
-- Adds phantom (wishlist) books: rows that exist as title + author only,
-- with no EPUB file yet. They live alongside real books and get attached
-- to a real file via ``LibraryService.attach_epub`` once available.
--
-- SQLite cannot relax a ``NOT NULL`` column in place, so we rebuild the
-- ``books`` table. The data migration carries every existing row across
-- with ``is_phantom = 0``.

CREATE TABLE books_new (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier      TEXT NOT NULL UNIQUE,
    file_path       TEXT,
    title           TEXT NOT NULL,
    authors         TEXT NOT NULL DEFAULT '',
    rating          INTEGER CHECK (rating IS NULL OR (rating BETWEEN 1 AND 5)),
    added_at        TEXT NOT NULL,
    completed_at    TEXT,
    last_opened_at  TEXT,
    is_phantom      INTEGER NOT NULL DEFAULT 0,
    CHECK (is_phantom = 1 OR file_path IS NOT NULL)
);

INSERT INTO books_new (
    id, identifier, file_path, title, authors, rating,
    added_at, completed_at, last_opened_at, is_phantom
)
SELECT id, identifier, file_path, title, authors, rating,
       added_at, completed_at, last_opened_at, 0
FROM books;

DROP TABLE books;
ALTER TABLE books_new RENAME TO books;

CREATE INDEX IF NOT EXISTS idx_books_last_opened ON books (last_opened_at DESC);
CREATE INDEX IF NOT EXISTS idx_books_phantom ON books (is_phantom);
