# Install

`bookreader-tui` is on PyPI. The bare `bookreader` name was taken, so the
PyPI distribution is `bookreader-tui`; the import path and the console
script are still `bookreader`.

## Recommended: pipx or uv tool

For end-user CLI tools, prefer an isolated install. On modern Linux distros
[PEP 668](https://peps.python.org/pep-0668/) blocks `pip install` into the
system Python anyway.

=== "pipx"

    ```bash
    pipx install bookreader-tui
    bookreader --version
    ```

=== "uv tool"

    ```bash
    uv tool install bookreader-tui
    bookreader --version
    ```

Both give you a global `bookreader` command with its dependencies sandboxed
in their own venv. Future upgrades: `pipx upgrade bookreader-tui` or
`uv tool upgrade bookreader-tui`.

## pip (inside a venv)

If you're already managing a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate            # Linux/macOS
# .venv\Scripts\activate             # Windows
pip install bookreader-tui
```

## From source

```bash
git clone https://github.com/prajwalmahajan101/BookReader
cd BookReader
pipx install -e .                    # or: pip install -e . inside a venv
```

## Requirements

| Requirement | Notes |
|---|---|
| Python ≥ 3.11 | Tested on 3.11, 3.12. |
| Terminal ≥ 80 columns | 120+ recommended. |
| Graphics-capable terminal | *Optional* — required only for inline images. See [terminal images](images.md). |

## Upgrading

```bash
pipx upgrade bookreader-tui          # or: uv tool upgrade bookreader-tui
```

Your library DB and reading positions are preserved across upgrades.

## Uninstall

```bash
pipx uninstall bookreader-tui        # or: uv tool uninstall bookreader-tui

# Optional: wipe the library and reading state too
rm -rf ~/.local/share/bookreader ~/.local/state/bookreader
```
