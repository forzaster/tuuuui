"""Left pane: a scrollable file tree.

Built on Textual's :class:`DirectoryTree` (already scrollable). When a file is
selected it re-emits a simpler :class:`Filer.FileOpened` message that the app
listens for, keeping the app decoupled from DirectoryTree internals.
"""

from __future__ import annotations

from pathlib import Path

from textual.binding import Binding
from textual.message import Message
from textual.widgets import DirectoryTree


class Filer(DirectoryTree):
    """File-system tree for the left pane.

    Adds emacs-style navigation on top of the default arrow keys:
    ``C-n``/``C-p`` move down/up, ``C-f``/``C-b`` expand/collapse (descend to
    child / ascend to parent), and ``C-v``/``M-v`` page down/up.
    """

    BINDINGS = [
        Binding("ctrl+n", "cursor_down", "Down", show=False),
        Binding("ctrl+p", "cursor_up", "Up", show=False),
        Binding("ctrl+f", "cursor_next_sibling", "Next", show=False),
        Binding("ctrl+b", "cursor_parent", "Parent", show=False),
        Binding("ctrl+v", "page_down", "Page down", show=False),
        Binding("alt+v", "page_up", "Page up", show=False),
    ]

    class FileOpened(Message):
        """Posted when the user selects a file in the tree."""

        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        event.stop()
        self.post_message(self.FileOpened(Path(event.path)))
