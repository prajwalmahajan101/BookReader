# Contributing to bookreader-tui

Thanks for considering it. The bar is high but the process is
mechanical — match it and your PR should sail through.

## Quick start

```bash
git clone https://github.com/prajwalmahajan101/BookReader
cd BookReader
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## The full local gate (CI runs the same thing)

```bash
pytest -q
ruff format --check . && ruff check src/ tests/
mypy src/
```

All three must be green before pushing. `pre-commit` will catch most
of this on commit; CI is the backstop.

## Branch + commit policy

- **Never commit to `main`.** Cut a branch named `feature/<topic>` or
  `fix/<topic>` or `docs/<topic>` and merge fast-forward.
- **Conventional commits.** Subject ≤ 72 chars, imperative mood, no
  trailing period:
  - `feat(scope): add X`
  - `fix(scope): handle Y`
  - `refactor(scope): …`
  - `docs(scope): …`
  - `test(scope): …`
  - `chore(scope): …`
- **Atomic commits.** One logical change per commit; no WIP commits
  on branches that will be PR'd.
- **No AI attribution.** Don't append `Co-Authored-By: Claude` or
  similar.
- **No `--no-verify` or `--no-gpg-sign`.** If a hook fails, fix the
  cause.

## Architectural conventions

- `core/` does no I/O. `epub/` does no UI or DB. `library/repository`
  does no business logic. UI never touches the DB — it goes through
  `library/service`.
- Errors subclass `BookReaderError`. The central handler in
  `ui/app.py` routes them. Don't blanket-catch `Exception`.
- Module-level logger via `bookreader.core.logging.get_logger(__name__)`.
- Type hints everywhere; mypy strict is the gate.
- `from __future__ import annotations` at the top of every module.
- PEP 257 + Google docstrings (`Args:` / `Returns:` / `Raises:`).

## When to write an ADR

Add `docs/adr/NNNN-<slug>.md` whenever you change:

- A persistence schema
- A protocol between layers (epub ↔ library ↔ ui)
- A dependency choice
- A user-visible behaviour that's not obvious from the code

Pattern: **Context · Decision · Consequences**. See existing ADRs
under `docs/adr/` for the shape.

## Pull requests

- One PR per logical change. Sub-phases are fine as separate PRs.
- PR description: what changed, why, how you verified, screenshots
  for UI changes.
- Make sure CI is green before requesting review.

## Releasing

Maintainer only — see the "Releasing" section of the
[README](./README.md#releasing). Tag-driven, fully automated via
`.github/workflows/release.yml`.
