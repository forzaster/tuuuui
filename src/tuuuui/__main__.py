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
    parser.add_argument(
        "--tmux",
        action="store_true",
        help="On launch, split a tmux pane to the right running the workspace CLI.",
    )
    parser.add_argument(
        "--workspace",
        metavar="CMD",
        default=None,
        help="Command to run in the workspace pane (default: $TUUUUI_WORKSPACE_CMD "
        "or 'claude').",
    )
    parser.add_argument(
        "--no-watch",
        dest="watch",
        action="store_false",
        help="Disable real-time file watching (no auto-refresh on external edits).",
    )
    args = parser.parse_args()
    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")
    TuuuuiApp(
        root,
        workspace_cmd=args.workspace,
        tmux_mode=args.tmux,
        watch=args.watch,
    ).run()


if __name__ == "__main__":
    main()
