"""Allow ``python -m bookreader …`` to dispatch to the CLI."""

from __future__ import annotations

from bookreader.cli import main

if __name__ == "__main__":
    main()
