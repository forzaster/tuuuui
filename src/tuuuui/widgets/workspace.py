"""Right pane: the workspace.

The interactive CLI (``claude code`` / Copilot CLI) is hosted in a *tmux* pane
beside this app rather than embedded as a PTY here (most stable). This widget
shows the workspace status and instructions; tmux layout integration lands in
Phase 4.
"""

from __future__ import annotations

import os

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static


class Workspace(Container):
    """Right pane placeholder / tmux status."""

    DEFAULT_CSS = """
    Workspace { height: 1fr; padding: 1; }
    Workspace #ws-body { height: 1fr; }
    """

    def compose(self) -> ComposeResult:
        yield Static(self._status_text(), id="ws-body")

    def _status_text(self) -> str:
        in_tmux = bool(os.environ.get("TMUX"))
        if in_tmux:
            return (
                "[b]Workspace[/b]\n\n"
                "Running inside tmux.\n"
                "Phase 4 will split a tmux pane here and launch\n"
                "[b]claude code[/b] / [b]copilot cli[/b].\n\n"
                "For now, open a tmux pane manually:\n"
                "  [dim]C-b %[/dim]  then run your CLI."
            )
        return (
            "[b]Workspace[/b]\n\n"
            "[yellow]Not running inside tmux.[/yellow]\n"
            "Start tmux and run this app to enable the\n"
            "workspace pane (claude code / copilot cli).\n\n"
            "  [dim]tmux new -s tuuuui[/dim]"
        )
