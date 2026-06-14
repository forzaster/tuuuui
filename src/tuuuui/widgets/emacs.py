"""Emacs keybindings layered onto Textual's ``TextArea``.

Scope (Phase 3): basic movement, deletion, a global kill-ring with
kill/yank/region, mark/point, undo, save (delegated to the app), and a simple
forward search. Full emacs (``M-x``, rectangles) is intentionally out of scope.

The kill ring is shared across all editors via a class attribute, matching
emacs' single global kill ring.
"""

from __future__ import annotations

from textual.binding import Binding
from textual.document._document import Location
from textual.widgets import TextArea

from .search import SearchScreen

# Type alias: a (row, column) location.
Loc = Location


def _ordered(a: Loc, b: Loc) -> tuple[Loc, Loc]:
    """Return (start, end) with start <= end."""
    return (a, b) if a <= b else (b, a)


class EmacsTextArea(TextArea):
    """A ``TextArea`` with emacs keybindings and a shared kill ring."""

    # Shared, emacs-style global kill ring (most-recent first).
    _kill_ring: list[str] = []

    BINDINGS = [
        # Movement
        Binding("ctrl+a", "cursor_line_start", "Home", show=False),
        Binding("ctrl+e", "cursor_line_end", "End", show=False),
        Binding("ctrl+f", "cursor_right", "Right", show=False),
        Binding("ctrl+b", "cursor_left", "Left", show=False),
        Binding("ctrl+n", "cursor_down", "Down", show=False),
        Binding("ctrl+p", "cursor_up", "Up", show=False),
        Binding("alt+f", "cursor_word_right", "Word right", show=False),
        Binding("alt+b", "cursor_word_left", "Word left", show=False),
        # Deletion
        Binding("ctrl+d", "delete_right", "Delete", show=False),
        Binding("ctrl+h", "delete_left", "Backspace", show=False),
        Binding("alt+d", "delete_word_right", "Kill word", show=False),
        # Kill ring / region
        Binding("ctrl+k", "kill_line", "Kill line", show=False),
        Binding("ctrl+y", "yank", "Yank", show=False),
        Binding("ctrl+w", "kill_region", "Kill region", show=False),
        Binding("alt+w", "copy_region", "Copy region", show=False),
        Binding("ctrl+space", "set_mark", "Set mark", show=False),
        Binding("ctrl+g", "keyboard_quit", "Quit", show=False),
        # History / search
        Binding("ctrl+underscore", "undo", "Undo", show=False),
        Binding("ctrl+s", "isearch", "Search", show=False),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._mark: Loc | None = None
        self._last_search: str = ""

    async def _on_key(self, event) -> None:
        """Intercept the second key of a C-x chord before inserting text.

        A focused ``TextArea`` inserts printable keys in its own ``_on_key``,
        ahead of any app-level binding. So when the app has a pending ``C-x``
        prefix we must consume the next key here and route it to the app's chord
        handler instead of typing it.
        """
        app = self.app
        if getattr(app, "cx_pending", False) and event.key != "ctrl+x":
            event.prevent_default()
            event.stop()
            app.complete_cx(event.key)
            return
        await super()._on_key(event)

    # ------------------------------------------------------------------ kill ring
    @classmethod
    def _push_kill(cls, text: str) -> None:
        if text:
            cls._kill_ring.insert(0, text)

    def action_kill_line(self) -> None:
        """Kill from point to end of line; at EOL, kill the newline."""
        if self.read_only:
            return
        row, col = self.cursor_location
        line = self.document.get_line(row)
        if col < len(line):
            start, end = (row, col), (row, len(line))
        elif row + 1 < self.document.line_count:
            start, end = (row, col), (row + 1, 0)  # the newline
        else:
            return  # end of document
        killed = self.get_text_range(start, end)
        self._push_kill(killed)
        self.delete(start, end)

    def action_yank(self) -> None:
        if self.read_only or not self._kill_ring:
            return
        self.insert(self._kill_ring[0])

    def _region(self) -> tuple[Loc, Loc] | None:
        if self._mark is None:
            return None
        return _ordered(self._mark, self.cursor_location)

    def action_kill_region(self) -> None:
        region = self._region()
        if region is None:
            self.notify("No mark set.", severity="warning")
            return
        start, end = region
        self._push_kill(self.get_text_range(start, end))
        if not self.read_only:
            self.delete(start, end)
        self._clear_mark()

    def action_copy_region(self) -> None:
        region = self._region()
        if region is None:
            self.notify("No mark set.", severity="warning")
            return
        start, end = region
        self._push_kill(self.get_text_range(start, end))
        self._clear_mark()
        self.notify("Region copied.")

    # ---------------------------------------------------------------- mark / point
    def action_set_mark(self) -> None:
        self._mark = self.cursor_location
        self.notify("Mark set.")

    def _clear_mark(self) -> None:
        self._mark = None

    def action_keyboard_quit(self) -> None:
        self._clear_mark()

    # ----------------------------------------------------------------------- search
    def action_isearch(self) -> None:
        def _go(query: str | None) -> None:
            if not query:
                return
            self._last_search = query
            self._search_forward(query)

        self.app.push_screen(SearchScreen(self._last_search), _go)

    def _search_forward(self, query: str) -> None:
        text = self.text
        start_index = self.document.get_index_from_location(self.cursor_location)
        found = text.find(query, start_index + 1)
        if found == -1:
            found = text.find(query, 0)  # wrap around
        if found == -1:
            self.notify(f"Not found: {query}", severity="warning")
            return
        loc = self.document.get_location_from_index(found)
        end = self.document.get_location_from_index(found + len(query))
        self.move_cursor(loc)
        self.selection = self.selection.__class__(loc, end)
