"""Connection management + migration runner for the SQLite library.

Opens a single :class:`sqlite3.Connection` per ``Database`` instance with
foreign keys enabled, row factory set, and the migrations directory walked
forward on construction. The library lives in
``<data_dir>/library.db`` by default.
"""

from __future__ import annotations

import sqlite3
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

from bookreader.core.logging import get_logger
from bookreader.core.paths import data_dir

if TYPE_CHECKING:
    from collections.abc import Iterator

log = get_logger(__name__)

_MIGRATIONS_PACKAGE = "bookreader.library.migrations"


def default_db_path() -> Path:
    """Return the default library database path."""
    return data_dir() / "library.db"


class Database:
    """A connected SQLite database with migrations applied.

    Use as a context manager or call :meth:`close` explicitly. The connection
    is reused for the life of the instance; the repositories share it.
    """

    def __init__(self, path: Path | None = None) -> None:
        """Open or create the database at *path* and migrate forward."""
        self._path = path or default_db_path()
        self._conn = sqlite3.connect(
            str(self._path),
            detect_types=sqlite3.PARSE_DECLTYPES,
            isolation_level=None,  # autocommit; explicit BEGIN in service
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._ensure_schema_table()
        self._migrate()

    # ----- context manager -------------------------------------------------

    def __enter__(self) -> Database:
        """Enter the runtime context."""
        return self

    def __exit__(self, *_: object) -> None:
        """Close the connection on context exit."""
        self.close()

    # ----- public API ------------------------------------------------------

    @property
    def conn(self) -> sqlite3.Connection:
        """Underlying connection; for repository use only."""
        return self._conn

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()

    # ----- migration runner ------------------------------------------------

    def _ensure_schema_table(self) -> None:
        """Create the bookkeeping table for applied migrations."""
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS _schema_version ("
            "  version INTEGER PRIMARY KEY,"
            "  applied_at TEXT NOT NULL"
            ")"
        )

    def _applied_versions(self) -> set[int]:
        """Return the set of migration numbers already applied."""
        rows = self._conn.execute("SELECT version FROM _schema_version").fetchall()
        return {row["version"] for row in rows}

    def _migrate(self) -> None:
        """Apply pending migrations in version order."""
        applied = self._applied_versions()
        for version, sql in _iter_migrations():
            if version in applied:
                continue
            log.info("applying migration %04d", version)
            self._conn.executescript("BEGIN; " + sql + "; COMMIT;")
            self._conn.execute(
                "INSERT INTO _schema_version (version, applied_at) VALUES (?, datetime('now'))",
                (version,),
            )


def _iter_migrations() -> Iterator[tuple[int, str]]:
    """Yield ``(version, sql)`` pairs from the migrations package, sorted."""
    files = sorted(
        (f for f in resources.files(_MIGRATIONS_PACKAGE).iterdir() if f.name.endswith(".sql")),
        key=lambda f: f.name,
    )
    for f in files:
        try:
            version = int(f.name.split("_", 1)[0])
        except ValueError:
            continue
        yield version, f.read_text(encoding="utf-8")
