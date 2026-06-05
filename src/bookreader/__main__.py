"""Allow ``python -m bookreader …`` to dispatch to the CLI."""

from __future__ import annotations

import sys

from bookreader.cli import _rewrite_path_sugar, main

if __name__ == "__main__":
    sys.argv = _rewrite_path_sugar(sys.argv)
    main()
