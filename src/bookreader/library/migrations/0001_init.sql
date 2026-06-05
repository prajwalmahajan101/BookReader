-- BookReader library schema, version 1.
--
-- Single-user SQLite. Foreign keys are enabled at connection time
-- (PRAGMA foreign_keys = ON) so cascades fire on book deletion.

CREATE TABLE IF NOT EXISTS books (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier      TEXT NOT NULL UNIQUE,
    file_path       TEXT NOT NULL,
    title           TEXT NOT NULL,
    authors         TEXT NOT NULL DEFAULT '',
    rating          INTEGER CHECK (rating IS NULL OR (rating BETWEEN 1 AND 5)),
    added_at        TEXT NOT NULL,
    completed_at    TEXT,
    last_opened_at  TEXT
);

CREATE INDEX IF NOT EXISTS idx_books_last_opened ON books (last_opened_at DESC);

CREATE TABLE IF NOT EXISTS collections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS book_collections (
    book_id        INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    collection_id  INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    PRIMARY KEY (book_id, collection_id)
);

CREATE TABLE IF NOT EXISTS positions (
    book_id        INTEGER PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,
    chapter_index  INTEGER NOT NULL DEFAULT 0,
    scroll_offset  INTEGER NOT NULL DEFAULT 0,
    page_index     INTEGER,
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookmarks (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id        INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_index  INTEGER NOT NULL,
    scroll_offset  INTEGER NOT NULL DEFAULT 0,
    note           TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bookmarks_book ON bookmarks (book_id);
