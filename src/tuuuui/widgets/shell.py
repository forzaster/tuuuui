"""Center pane (shell mode): a lightweight, non-interactive command runner.

Type a command and press Enter; it runs through the shell with the app's root as
the working directory, and its combined stdout/stderr is appended to a scrollable
log (after an echo of the command). ``C-n``/``C-p`` walk the command history,
like the other list views.

This is deliberately **not** a PTY — full-screen interactive programs (``vim``,
``top``, ``less`` …) are not supported. Use the tmux workspace pane (``C-x t``)
for those. Keeping it subprocess-based makes it stable and dependency-free, in
line with the project's "tmux over embedded PTY" stance.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Input, RichLog

from ..core import shell


class ShellInput(Input):
    """Command input; ``C-p``/``C-n`` recall previous/next history entries."""

    BINDINGS = [
        Binding("ctrl+p", "history_prev", "History prev", show=False),
        Binding("ctrl+n", "history_next", "History next", show=False),
    ]

    def __init__(self, view: "ShellView", **kwargs) -> None:
        super().__init__(**kwargs)
        self._view = view

    def action_history_prev(self) -> None:
        self._view.history_prev()

    def action_history_next(self) -> None:
        self._view.history_next()


class ShellView(Vertical):
    """An output log over a one-line command input."""

    DEFAULT_CSS = """
    ShellView { height: 1fr; }
    ShellView #shell-log { height: 1fr; border-bottom: solid $accent; padding: 0 1; }
    ShellView #shell-input { dock: bottom; height: 1; border: none; padding: 0 1; }
    """

    def __init__(self, cwd: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._cwd = cwd
        self._history: list[str] = []
        # Index into history while browsing it; None means "at a fresh prompt".
        self._hist_index: int | None = None

    def compose(self) -> ComposeResult:
        yield RichLog(id="shell-log", highlight=False, markup=False, wrap=True)
        yield ShellInput(
            self, placeholder="$ command (Enter to run)", id="shell-input"
        )

    @property
    def log(self) -> RichLog:
        return self.query_one("#shell-log", RichLog)

    @property
    def input(self) -> Input:
        return self.query_one("#shell-input", Input)

    # ----------------------------------------------------------------- running
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "shell-input":
            return
        event.stop()
        cmd = event.value.strip()
        self.input.value = ""
        self._hist_index = None
        if not cmd:
            return
        self._history.append(cmd)
        self.log.write(f"$ {cmd}")
        self.run_worker(self._run(cmd), group="shell")

    async def _run(self, cmd: str) -> None:
        try:
            output, returncode = await shell.run_command(cmd, self._cwd)
        except OSError as exc:
            self.log.write(f"[error: {exc}]")
            return
        text = output.rstrip("\n")
        if text:
            self.log.write(text)
        if returncode:
            self.log.write(f"[exit {returncode}]")

    # --------------------------------------------------------------- history
    def history_prev(self) -> None:
        if not self._history:
            return
        if self._hist_index is None:
            self._hist_index = len(self._history) - 1
        else:
            self._hist_index = max(0, self._hist_index - 1)
        self._set_input(self._history[self._hist_index])

    def history_next(self) -> None:
        if self._hist_index is None:
            return
        if self._hist_index >= len(self._history) - 1:
            self._hist_index = None
            self._set_input("")
            return
        self._hist_index += 1
        self._set_input(self._history[self._hist_index])

    def _set_input(self, value: str) -> None:
        inp = self.input
        inp.value = value
        inp.cursor_position = len(value)
