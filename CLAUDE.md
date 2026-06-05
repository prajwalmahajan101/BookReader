# BookReader — Project Conventions

A terminal EPUB reader and library, built with Textual. See plan at
`~/.claude/plans/moonlit-popping-sunset.md`.

## Stack

- Python ≥ 3.10, async-first
- Textual (TUI), ebooklib + bs4 + lxml (EPUB), pydantic-settings (config)
- SQLite via stdlib `sqlite3` (Phase 2+); JSON state file (Phase 1)
- Ruff (format + lint), mypy strict, pytest (`asyncio_mode = auto`)
- pip-tools (`requirements/*.in` → `*.txt`), pre-commit enforced

## Layout

`src/` layout. Layered:

| Layer       | Responsibility                                       |
|-------------|------------------------------------------------------|
| `core/`     | Config, paths, logging, exception hierarchy. No I/O. |
| `epub/`     | Parse + render EPUB. Pure: no UI, no DB.             |
| `library/`  | (Phase 2) Persistence + business logic.              |
| `ui/`       | Textual app, screens, widgets. No DB access.         |

UI never imports from a repository directly — it goes through a service.

## Code Style

- `from __future__ import annotations` at the top of every module.
- Type hints everywhere; mypy strict is the gate.
- PEP 257 + Google docstrings (`Args:` / `Returns:` / `Raises:`).
- Module-level logger via `bookreader.core.logging.get_logger(__name__)`.
- Errors: subclass `BookReaderError`. Raise specific. Never silent-except.
- No fallback values that mask failures.

## Commit Discipline

- Conventional commits: `feat(scope): …`, `fix(scope): …`, `refactor`, `docs`, `test`, `chore`.
- Subject ≤ 72 chars, imperative, no trailing period.
- Atomic — one logical change per commit.
- Explicit staging: `git add src/path/file.py`. Never `git add .` / `-A`.
- Never `--no-verify`. Never amend pushed commits. No AI attribution footer.
- `main` is releasable. Work on `feature/phaseN_<topic>` branches.

## Testing

- Unit tests for `epub/` and `library/repository`. Integration for `library/service`.
- Sample EPUB fixture under `tests/fixtures/` (public domain only).
- Async tests with `async def test_*`.

## ADRs

`docs/adr/NNNN-slug.md`. Update / add when an architectural decision changes.
