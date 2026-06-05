"""A minimal status strip above the footer.

Shows: ``Chapter title · 3 / 24 · ▰▰▰▰▰▱▱▱▱▱  42%``. Updated by the
ReaderScreen whenever the chapter or scroll position changes. Keeping it as
a small custom widget rather than abusing the Footer keeps the footer-hint
strip clean.
"""

from __future__ import annotations

from textual.widgets import Static

_BAR_WIDTH = 14
_FILLED = "▰"
_EMPTY = "▱"


class StatusBar(Static):
    """One-line reading-progress display."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        padding: 0 2;
        content-align: left middle;
    }
    """

    def set_state(
        self,
        *,
        chapter_title: str,
        chapter_index: int,
        chapter_count: int,
        progress: float,
    ) -> None:
        """Update the status line.

        Args:
            chapter_title: Title of the current chapter.
            chapter_index: Zero-based chapter index.
            chapter_count: Total chapters in the book.
            progress: Fraction of overall book read in ``[0.0, 1.0]``.
        """
        clamped = max(0.0, min(1.0, progress))
        filled = round(clamped * _BAR_WIDTH)
        bar = _FILLED * filled + _EMPTY * (_BAR_WIDTH - filled)
        pct = round(clamped * 100)

        # Use Textual content markup so colours follow the active theme
        # instead of hard-coded styles. `$accent` and `$foreground-muted`
        # resolve from the registered theme.
        self.update(
            f"[bold]{chapter_title}[/]"
            f"  [$foreground-muted]·[/]  "
            f"[$foreground-muted]{chapter_index + 1}/{chapter_count}[/]"
            f"  [$foreground-muted]·[/]  "
            f"[$accent]{bar}[/]"
            f"  [$foreground-muted]{pct:>3d}%[/]"
        )
