"""Right pane: the workspace status.

The interactive CLI (``claude code`` / Copilot CLI) runs in a real *tmux* pane
split to the right of the app rather than embedded here (most stable). This
widget shows how to launch it and reflects whether tmux is available. The actual
split is performed by :mod:`tuuuui.core.tmux` (triggered by ``C-x t`` or
``--tmux`` at launch).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Static

from ..core import tmux


class Workspace(Container):
    """Right pane: tmux workspace status / instructions."""

    DEFAULT_CSS = """
    Workspace { height: 1fr; padding: 1; }
    Workspace #ws-body { height: 1fr; }
    """

    command: reactive[str] = reactive(tmux.DEFAULT_WORKSPACE_CMD)
    running: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static(self._status_text(), id="ws-body")

    def watch_command(self) -> None:
        self._refresh()

    def watch_running(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        try:
            self.query_one("#ws-body", Static).update(self._status_text())
        except Exception:
            pass  # not mounted yet

    def _status_text(self) -> str:
        if self.running:
            return (
                "[b]Workspace[/b]\n\n"
                f"[green]Running in a tmux pane:[/green]\n  [b]{self.command}[/b]\n\n"
                "Switch to it with your tmux key:\n"
                "  [dim]C-b →[/dim]  (move to the right pane)"
            )
        if not tmux.is_inside_tmux():
            return (
                "[b]Workspace[/b]\n\n"
                "[yellow]Not running inside tmux.[/yellow]\n"
                "Start tmux, then relaunch to enable the\n"
                "workspace pane.\n\n"
                "  [dim]tmux new -s tuuuui[/dim]\n"
                "  [dim]tuuuui --tmux[/dim]"
            )
        return (
            "[b]Workspace[/b]\n\n"
            "Inside tmux. Open the workspace pane with\n"
            "  [b]C-x t[/b]\n\n"
            f"It will run: [b]{self.command}[/b]\n"
            "[dim](set via --workspace CMD or\n TUUUUI_WORKSPACE_CMD)[/dim]"
        )
