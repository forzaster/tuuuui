"""tmux integration for the right-hand workspace pane.

Rather than embedding a PTY inside the app, the interactive CLI (``claude code``
/ Copilot CLI) runs in a real tmux pane split to the right of the app. These
helpers build and run the tmux commands; the argv builders are pure so they can
be unit tested without tmux installed.
"""

from __future__ import annotations

import os
import shutil
import subprocess

# Default command for the workspace pane; overridable via env or CLI flag.
DEFAULT_WORKSPACE_CMD = os.environ.get("TUUUUI_WORKSPACE_CMD", "claude")


def is_inside_tmux() -> bool:
    """True if the current process is running inside a tmux session."""
    return bool(os.environ.get("TMUX"))


def tmux_available() -> bool:
    """True if the tmux binary is on PATH."""
    return shutil.which("tmux") is not None


def split_right_argv(command: str, percent: int = 30, focus: bool = False) -> list[str]:
    """Build the ``tmux split-window`` argv that opens *command* to the right.

    *percent* is the width of the new pane. When *focus* is False the new pane
    is created detached (``-d``) so focus stays on the app.
    """
    argv = ["tmux", "split-window", "-h", "-l", f"{percent}%"]
    if not focus:
        argv.append("-d")
    argv.append(command)
    return argv


def spawn_workspace(
    command: str = DEFAULT_WORKSPACE_CMD,
    percent: int = 30,
    focus: bool = False,
) -> tuple[bool, str]:
    """Split a tmux pane to the right running *command*.

    Returns ``(ok, message)``. Never raises; failures are reported in *message*.
    """
    if not is_inside_tmux():
        return (False, "Not inside tmux. Start tmux and relaunch.")
    if not tmux_available():
        return (False, "tmux is not installed or not on PATH.")
    try:
        subprocess.run(
            split_right_argv(command, percent, focus),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        return (False, exc.stderr.strip() or "tmux split-window failed")
    return (True, f"Workspace running: {command}")
