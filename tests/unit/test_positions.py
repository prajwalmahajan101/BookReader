"""Tests for ``bookreader.state.positions``."""

from __future__ import annotations

from pathlib import Path

from bookreader.state.positions import PositionStore


def test_save_then_get_roundtrips(tmp_path: Path) -> None:
    store = PositionStore(tmp_path / "positions.json")
    store.save("book-id-1", chapter_index=4, scroll_offset=120)

    pos = store.get("book-id-1")
    assert pos is not None
    assert pos.chapter_index == 4
    assert pos.scroll_offset == 120
    assert pos.updated_at


def test_get_missing_returns_none(tmp_path: Path) -> None:
    store = PositionStore(tmp_path / "positions.json")
    assert store.get("nope") is None


def test_state_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "positions.json"
    PositionStore(path).save("id", chapter_index=2, scroll_offset=10)

    pos = PositionStore(path).get("id")
    assert pos is not None
    assert pos.chapter_index == 2
    assert pos.scroll_offset == 10
