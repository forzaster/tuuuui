"""Center pane (rgrep mode): recursive-grep across the project.

Top: a search input. Submit (Enter) runs ripgrep over the repository root.
Bottom: one row per matching line. Highlighting a row previews ``path:line``;
selecting a row asks the app to open that file at the match via
:class:`RGrepView.OpenMatch`.

The actual search lives in :mod:`tuuuui.core.rgrep`, so this widget stays a thin
UI layer with no subprocess logic of its own.
"""

from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from ..core import rgrep


class RGrepView(Vertical):
    """Search input over a scrollable list of matching lines."""

    class OpenMatch(Message):
        """Posted when a result is selected; carries the file and 1-based line."""

        def __init__(self, path: Path, line: int) -> None:
            self.path = path
            self.line = line
            super().__init__()

    DEFAULT_CSS = """
    RGrepView { height: 1fr; }
    RGrepView #rgrep-input { height: 3; border: tall $accent; }
    RGrepView #rgrep-status { height: 1; background: $panel; padding: 0 1; }
    RGrepView #rgrep-results-scroll { height: 1fr; }
    RGrepView #rgrep-results { height: auto; }
    """

    def __init__(self, root: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._root = root
        # Matches backing the result list, parallel to the option order.
        self._matches: list[rgrep.Match] = []

    def compose(self) -> ComposeResult:
        yield Input(placeholder="rgrep (Enter to search)…", id="rgrep-input")
        yield Static("Type a pattern and press Enter.", id="rgrep-status")
        with VerticalScroll(id="rgrep-results-scroll"):
            yield OptionList(id="rgrep-results")

    @property
    def input(self) -> Input:
        return self.query_one("#rgrep-input", Input)

    def focus_input(self) -> None:
        self.input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "rgrep-input":
            return
        event.stop()
        pattern = event.value.strip()
        if not pattern:
            self._set_status("Type a pattern and press Enter.")
            return
        self.run_worker(self._search(pattern), group="rgrep", exclusive=True)

    async def _search(self, pattern: str) -> None:
        self._set_status(f"Searching for {pattern!r}…")
        try:
            matches = await rgrep.search(self._root, pattern)
        except rgrep.RGrepError as exc:
            self._matches = []
            self.query_one("#rgrep-results", OptionList).clear_options()
            self._set_status(f"rgrep error: {exc}")
            return
        self._populate(matches)
        count = len(matches)
        suffix = "" if count == 1 else "es"
        self._set_status(f"{count} match{suffix} for {pattern!r}")

    def _populate(self, matches: list[rgrep.Match]) -> None:
        self._matches = matches
        results = self.query_one("#rgrep-results", OptionList)
        results.clear_options()
        results.add_options(
            Option(Text(m.one_line(self._root)), id=str(i))
            for i, m in enumerate(matches)
        )

    def _set_status(self, text: str) -> None:
        self.query_one("#rgrep-status", Static).update(text)

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        if event.option_list.id != "rgrep-results":
            return
        event.stop()
        match = self._match_for(event.option.id)
        if match is not None:
            self.post_message(self.OpenMatch(match.path, match.line))

    def _match_for(self, option_id: str | None) -> rgrep.Match | None:
        if option_id is None:
            return None
        try:
            return self._matches[int(option_id)]
        except (ValueError, IndexError):
            return None
