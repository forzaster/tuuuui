"""``C-x b`` buffer switcher: a modal list of opened files.

Shows :class:`~tuuuui.core.buffers.BufferManager` entries in most-recently-used
order. Enter (or click) picks one; Escape cancels. The previously-used buffer is
pre-highlighted, like emacs.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from ..core.buffers import BufferManager


class BufferList(ModalScreen[Path | None]):
    """Modal that returns the chosen buffer path (or None if cancelled)."""

    BINDINGS = [Binding("escape", "dismiss(None)", "Cancel")]

    DEFAULT_CSS = """
    BufferList { align: center middle; }
    BufferList > Vertical {
        width: 60; height: auto; max-height: 80%;
        border: thick $accent; background: $panel;
    }
    BufferList #title { padding: 0 1; background: $accent; color: $text; }
    BufferList OptionList { height: auto; max-height: 20; }
    """

    def __init__(self, manager: BufferManager) -> None:
        super().__init__()
        self._manager = manager

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Switch to buffer (C-x b)", id="title")
            options = [
                Option(self._label(b.path), id=str(b.path))
                for b in self._manager.buffers
            ]
            yield OptionList(*options, id="buffers")

    def _label(self, path: Path) -> str:
        return f"{path.name}    [dim]{path.parent}[/dim]"

    def on_mount(self) -> None:
        option_list = self.query_one("#buffers", OptionList)
        if option_list.option_count == 0:
            return
        # Pre-select the previous buffer (2nd MRU) if it exists, else current.
        index = 1 if self._manager.previous is not None else 0
        option_list.highlighted = index
        option_list.focus()

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        self.dismiss(Path(event.option.id) if event.option.id else None)
