"""``tuuuui-tmux`` — one command to launch tmux with tuuuui + a workspace pane.

Creates (or reuses) a tmux session whose left pane runs the tuuuui app and whose
right pane runs an interactive CLI (``claude`` / Copilot CLI), then attaches.

If already inside tmux, it instead splits the current window (delegating to
``tuuuui --tmux``) rather than nesting a new session.

The tmux command construction lives in :func:`tmux_setup_argv` as a pure function
so it can be unit tested without tmux installed.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from .core import tmux


def _app_command(path: Path) -> str:
    """Command that launches the tuuuui app, using the current interpreter."""
    return f"{shlex.quote(sys.executable)} -m tuuuui {shlex.quote(str(path))}"


def tmux_setup_argv(
    session: str,
    left_cmd: str,
    right_cmd: str,
    percent: int = 30,
) -> list[list[str]]:
    """Build the tmux commands that set up the two-pane session (no attach).

    Returns a list of argv lists: create a detached session running *left_cmd*,
    split a right pane (*percent* wide) running *right_cmd*, then put focus back
    on the left pane.
    """
    return [
        ["tmux", "new-session", "-d", "-s", session, left_cmd],
        ["tmux", "split-window", "-h", "-d", "-l", f"{percent}%", "-t", session, right_cmd],
        ["tmux", "select-pane", "-L", "-t", session],
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tuuuui-tmux",
        description="Launch tmux with tuuuui (left) and a workspace CLI (right).",
    )
    parser.add_argument("path", nargs="?", default=".", help="Directory to open.")
    parser.add_argument(
        "--workspace",
        metavar="CMD",
        default=tmux.DEFAULT_WORKSPACE_CMD,
        help="Command for the right pane (default: $TUUUUI_WORKSPACE_CMD or 'claude').",
    )
    parser.add_argument("--session", default="tuuuui", help="tmux session name.")
    parser.add_argument(
        "--percent", type=int, default=30, help="Width %% of the workspace pane."
    )
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")
    if not 1 <= args.percent <= 99:
        parser.error("--percent must be between 1 and 99")
    if not tmux.tmux_available():
        parser.error("tmux is not installed or not on PATH.")

    # Already inside tmux: don't nest a session — split the current window.
    if tmux.is_inside_tmux():
        os.execvp(
            sys.executable,
            [sys.executable, "-m", "tuuuui", "--tmux", "--workspace", args.workspace,
             str(root)],
        )
        return  # not reached

    if tmux.session_exists(args.session):
        parser.error(
            f"tmux session '{args.session}' already exists; "
            f"attach with 'tmux attach -t {args.session}' or pass --session NAME"
        )

    try:
        for argv in tmux_setup_argv(
            args.session, _app_command(root), args.workspace, args.percent
        ):
            subprocess.run(argv, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        # Roll back a half-created session so we don't leave it detached.
        subprocess.run(
            ["tmux", "kill-session", "-t", args.session],
            capture_output=True,
        )
        parser.error(exc.stderr.strip() or "tmux setup failed")

    # Attach in the foreground (blocks until the session ends).
    os.execvp("tmux", ["tmux", "attach-session", "-t", args.session])


if __name__ == "__main__":
    main()
