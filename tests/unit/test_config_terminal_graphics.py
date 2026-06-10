"""Phase 5.0c — auto-enable images when the terminal supports graphics.

``Settings.images_enabled`` defaults to True in kitty / iTerm2 / WezTerm
(detected by env vars). An explicit ``BOOKREADER_IMAGES_ENABLED`` env
var always wins over the auto-detected default — so users on
unsupported terminals can still opt in, and users on supported
terminals can opt out.
"""

from __future__ import annotations

import pytest

from bookreader.core.config import load_settings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip every env var that influences detection before each test."""
    for var in (
        "BOOKREADER_IMAGES_ENABLED",
        "KITTY_WINDOW_ID",
        "TERM",
        "TERM_PROGRAM",
    ):
        monkeypatch.delenv(var, raising=False)


def test_default_off_on_unknown_terminal() -> None:
    assert load_settings().images_enabled is False


def test_default_on_in_kitty_via_term(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERM", "xterm-kitty")
    assert load_settings().images_enabled is True


def test_default_on_in_kitty_via_window_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KITTY_WINDOW_ID", "5")
    assert load_settings().images_enabled is True


def test_default_on_in_iterm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERM_PROGRAM", "iTerm.app")
    assert load_settings().images_enabled is True


def test_default_on_in_wezterm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERM_PROGRAM", "WezTerm")
    assert load_settings().images_enabled is True


def test_explicit_env_var_wins_over_dumb_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Even on a non-graphics terminal, the env var forces images on."""
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setenv("BOOKREADER_IMAGES_ENABLED", "1")
    assert load_settings().images_enabled is True


def test_explicit_env_var_wins_over_kitty_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """A user in kitty can still opt out with BOOKREADER_IMAGES_ENABLED=0."""
    monkeypatch.setenv("TERM", "xterm-kitty")
    monkeypatch.setenv("BOOKREADER_IMAGES_ENABLED", "0")
    assert load_settings().images_enabled is False
