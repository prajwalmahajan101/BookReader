"""Runtime settings for BookReader.

All values are overridable via environment variables prefixed ``BOOKREADER_``.
The TUI's default theme, scroll size, and TOC visibility live here so they are
adjustable without code edits.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Short, human-friendly theme name. The Textual theme id is
# ``bookreader-<short>``; the mapping happens in :mod:`bookreader.ui.app`.
ThemeName = Literal["dark", "light", "sepia"]
Theme = ThemeName  # backwards-compatible alias


class Settings(BaseSettings):
    """Top-level runtime configuration.

    Attributes:
        theme: Active color theme.
        line_scroll: Lines moved by ``j``/``k``.
        page_scroll_pct: Page jump as a percentage of viewport height.
        show_toc_default: Whether the TOC sidebar is open at startup.
        images_enabled: If true, attempt kitty/sixel inline image rendering
            (Phase 3). Phase 1 ignores this and always shows placeholders.
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
    images_enabled: bool = False
    two_page_default: bool = False


def load_settings() -> Settings:
    """Build a :class:`Settings` instance from environment and ``.env``."""
    return Settings()
