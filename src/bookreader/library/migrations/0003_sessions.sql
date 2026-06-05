-- BookReader library schema, version 3.
--
-- Reading sessions. One row per reader-screen open / quit cycle.
-- ``ended_at`` is NULL while the session is still open; we set it when
-- the user quits the reader (or — defensively — at next service start).

CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    pages_advanced  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sessions_book ON sessions (book_id, started_at DESC);
