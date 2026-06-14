"""A minimal yes/no confirmation modal.

Returns ``True`` if confirmed, ``False`` otherwise. ``y`` / ``n`` and the buttons
both work; Escape cancels (``False``).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmScreen(ModalScreen[bool]):
    """Modal that resolves to a boolean confirmation."""

    BINDINGS = [
        Binding("y", "confirm(True)", "Yes"),
        Binding("n", "confirm(False)", "No"),
        Binding("escape", "confirm(False)", "Cancel"),
    ]

    DEFAULT_CSS = """
    ConfirmScreen { align: center middle; }
    ConfirmScreen > Vertical {
        width: 56; height: auto; padding: 1 2;
        border: thick $warning; background: $panel;
    }
    ConfirmScreen #message { padding-bottom: 1; }
    ConfirmScreen Horizontal { height: auto; align-horizontal: right; }
    ConfirmScreen Button { margin-left: 2; }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._message, id="message")
            with Horizontal():
                yield Button("No", id="no")
                yield Button("Yes", id="yes", variant="error")

    def action_confirm(self, value: bool) -> None:
        self.dismiss(value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")
