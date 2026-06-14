"""Minimal incremental-ish search prompt (emacs ``C-s``).

A modal input that returns the query string (or None if cancelled). The editor
does the actual jump-to-match so search stays decoupled from this widget.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Input


class SearchScreen(ModalScreen[str | None]):
    """Prompt for a search query; returns the submitted string or None."""

    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    DEFAULT_CSS = """
    SearchScreen { align: center top; }
    SearchScreen Input {
        width: 50%; margin-top: 2; border: thick $accent;
    }
    """

    def __init__(self, initial: str = "") -> None:
        super().__init__()
        self._initial = initial

    def compose(self) -> ComposeResult:
        yield Input(value=self._initial, placeholder="I-search: ", id="search")

    def on_mount(self) -> None:
        inp = self.query_one(Input)
        inp.focus()
        inp.cursor_position = len(self._initial)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_dismiss(self) -> None:  # type: ignore[override]
        self.dismiss(None)
