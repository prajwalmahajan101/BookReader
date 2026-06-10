"""Runtime settings for BookReader.

All values are overridable via environment variables prefixed ``BOOKREADER_``.
The TUI's default theme, scroll size, and TOC visibility live here so they are
adjustable without code edits.
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Short, human-friendly theme name. The Textual theme id is
# ``bookreader-<short>``; the mapping happens in :mod:`bookreader.ui.app`.
ThemeName = Literal["dark", "light", "sepia"]
Theme = ThemeName  # backwards-compatible alias


def _terminal_supports_graphics() -> bool:
    """Best-effort detection of a graphics-capable terminal.

    Returns true when the active terminal advertises kitty's graphics
    protocol (``TERM=xterm-kitty`` or ``KITTY_WINDOW_ID``), iTerm2's
    inline-images extension, or WezTerm — all of which ``textual-image``
    can drive. Sixel-only emulators (xterm with sixel build, mlterm,
    foot) aren't auto-detected because there is no portable env-var
    signal; users can still opt in via ``BOOKREADER_IMAGES_ENABLED=1``.
    """
    if os.environ.get("KITTY_WINDOW_ID"):
        return True
    if os.environ.get("TERM", "") == "xterm-kitty":
        return True
    return os.environ.get("TERM_PROGRAM", "") in {"iTerm.app", "WezTerm"}


class Settings(BaseSettings):
    """Top-level runtime configuration.

    Attributes:
        theme: Active color theme.
        line_scroll: Lines moved by ``j``/``k``.
        page_scroll_pct: Page jump as a percentage of viewport height.
        show_toc_default: Whether the TOC sidebar is open at startup.
        images_enabled: If true, attempt kitty/sixel inline image rendering.
            Defaults to true when the terminal advertises a graphics
            protocol (kitty, iTerm2, WezTerm); otherwise false. An
            explicit ``BOOKREADER_IMAGES_ENABLED`` env var always wins.
    """

    model_config = SettingsConfigDict(
        env_prefix="BOOKREADER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    theme: ThemeName = "dark"
    line_scroll: int = Field(default=1, ge=1, le=10)
    page_scroll_pct: int = Field(default=90, ge=10, le=100)
    show_toc_default: bool = True
    images_enabled: bool = Field(default_factory=_terminal_supports_graphics)
    two_page_default: bool = False
    # Reading column max width in terminal cells. 84 was the old typography
    # cap (~70-character reading measure); bumped to 110 because images
    # and modern wide-screen terminals make the tight measure feel cramped.
    # Override with BOOKREADER_READING_WIDTH=N. Capped at 200 to keep
    # typography sane.
    reading_width: int = Field(default=110, ge=60, le=200)


def load_settings() -> Settings:
    """Build a :class:`Settings` instance from environment and ``.env``."""
    return Settings()
