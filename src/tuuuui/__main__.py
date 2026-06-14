"""Entry point: ``tuuuui [PATH]`` opens the IDE rooted at PATH (default: cwd)."""

from __future__ import annotations

import argparse
from pathlib import Path

from .app import TuuuuiApp


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tuuuui", description="A 3-pane terminal IDE built with Textual."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to open (default: current directory).",
    )
    args = parser.parse_args()
    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")
    TuuuuiApp(root).run()


if __name__ == "__main__":
    main()
