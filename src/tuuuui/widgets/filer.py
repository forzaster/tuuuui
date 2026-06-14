"""Left pane: a scrollable file tree.

Built on Textual's :class:`DirectoryTree` (already scrollable). When a file is
selected it re-emits a simpler :class:`Filer.FileOpened` message that the app
listens for, keeping the app decoupled from DirectoryTree internals.
"""

from __future__ import annotations

from pathlib import Path

from textual.message import Message
from textual.widgets import DirectoryTree


class Filer(DirectoryTree):
    """File-system tree for the left pane."""

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
