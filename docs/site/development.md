# Development

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

All three must be green before pushing.

## Project layout

```
src/bookreader/
  core/      # config, paths, logging, exceptions    (no I/O)
  epub/      # parsing + rendering                   (no UI, no DB)
  state/     # JSON position + bookmark fallback
  library/   # SQLite library: db, repo, service, migrations
  ui/        # Textual app, screens, widgets, themes
tests/
  unit/         # parsers, renderer, config
  integration/  # service + screen pilot tests
docs/
  adr/         # architecture decision records
  site/        # mkdocs-material source for this site
  screenshots/ # README/PyPI screenshots
scripts/
  capture_screenshots.py  # regenerates docs/screenshots/*.svg
```

UI never imports a repository directly — it goes through `library/service`.

## Architectural conventions

- `core/` does no I/O. `epub/` does no UI or DB. `library/repository`
  does no business logic.
- Errors subclass `BookReaderError`; the central handler in `ui/app.py`
  routes them. Don't blanket-catch `Exception`.
- Module-level logger via `bookreader.core.logging.get_logger(__name__)`.
- Type hints everywhere; mypy strict is the gate.
- `from __future__ import annotations` at the top of every module.
- PEP 257 + Google docstrings.

## Branch + commit policy

- Never commit to `main` — cut a `feature/<topic>` / `fix/<topic>` /
  `docs/<topic>` branch and fast-forward merge.
- Conventional commits: `feat|fix|refactor|docs|test|chore(scope): …`.
  Subject ≤ 72 chars, imperative, no trailing period.
- Atomic commits: one logical change each.
- Never `--no-verify`. Never amend pushed commits.
- No AI attribution footer.

See [CONTRIBUTING.md](https://github.com/prajwalmahajan101/BookReader/blob/main/CONTRIBUTING.md)
for the full policy.

## Regenerating screenshots

```bash
python scripts/capture_screenshots.py
```

Writes `docs/screenshots/{library,reader,reader-paged}.svg`. Re-run
whenever the UI changes meaningfully.

## Running the docs site locally

```bash
pip install -e ".[docs]"
mkdocs serve
# opens http://127.0.0.1:8000
```

## Releasing

Maintainer only. Tag-driven, fully automated via
`.github/workflows/release.yml`:

```bash
# 1. Bump version in two places
$EDITOR src/bookreader/__init__.py        # __version__ = "X.Y.Z"
$EDITOR pyproject.toml                    # version = "X.Y.Z"

# 2. Add a [X.Y.Z] section to CHANGELOG.md

# 3. Commit, tag, push
git commit -am "chore(release): bump to X.Y.Z"
git tag -a vX.Y.Z -m "Release X.Y.Z"
git push origin main vX.Y.Z
```

The workflow builds sdist + wheel, verifies the tag matches
`pyproject.toml`, publishes to PyPI via trusted publishing, and creates a
GitHub Release.
