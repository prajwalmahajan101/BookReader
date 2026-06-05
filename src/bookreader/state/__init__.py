"""Phase-1 persistence: a small JSON-backed positions store.

Phase 2 replaces this with the SQLite ``library`` layer. Keeping it isolated
under ``bookreader.state`` makes the swap a one-import change in the UI.
"""

from __future__ import annotations

from bookreader.state.positions import Position, PositionStore

__all__ = ["Position", "PositionStore"]
