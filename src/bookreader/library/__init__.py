"""Personal library: SQLite-backed persistence for books and collections.

Layered structure (mirroring ``colending_partner``):

- :mod:`bookreader.library.models` — frozen dataclasses (no I/O).
- :mod:`bookreader.library.repository` — thin sqlite3 wrappers.
- :mod:`bookreader.library.service` — business logic; the only consumer of
  the repositories. The UI talks to the service, never to a repository or
  raw connection.

Phase 2 adds collections, ratings, completion, and a recents view to the
reader from Phase 1.
"""

from __future__ import annotations
