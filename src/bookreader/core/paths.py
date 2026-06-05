"""XDG-correct paths for BookReader data, state, cache, and config.

Wraps :mod:`platformdirs` so the rest of the code never hard-codes paths or
falls back to ``~/.config`` style assumptions. All directories are created
lazily on first access.
"""

from __future__ import annotations

from pathlib import Path

from platformdirs import PlatformDirs

_APP_NAME = "bookreader"
_APP_AUTHOR = "bookreader"

_dirs = PlatformDirs(appname=_APP_NAME, appauthor=_APP_AUTHOR)


def _ensure(path: Path) -> Path:
    """Create *path* if missing and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_dir() -> Path:
    """Return the user config directory (e.g. ``~/.config/bookreader``)."""
    return _ensure(Path(_dirs.user_config_dir))


def data_dir() -> Path:
    """Return the user data directory (library DB lives here in Phase 2)."""
    return _ensure(Path(_dirs.user_data_dir))


def state_dir() -> Path:
    """Return the user state directory (positions / bookmarks file)."""
    return _ensure(Path(_dirs.user_state_dir))


def cache_dir() -> Path:
    """Return the user cache directory (chapter render cache)."""
    return _ensure(Path(_dirs.user_cache_dir))


def log_dir() -> Path:
    """Return the user log directory (single file: ``bookreader.log``)."""
    return _ensure(Path(_dirs.user_log_dir))


def positions_file() -> Path:
    """Return the path to the JSON positions file used in Phase 1."""
    return state_dir() / "positions.json"
