"""Center pane: swaps between the git view, the file view and the rgrep view.

Defaults to the git view ("while working"); opening a file from the filer
switches to the file view. ``C-x g`` switches back to git, ``C-x r`` to rgrep.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.widgets import ContentSwitcher

from .file_view import FileView
from .git_view import GitView
from .rgrep_view import RGrepView


class Center(ContentSwitcher):
    """ContentSwitcher holding the git view, the file view and the rgrep view."""

    def __init__(self, repo: Path, **kwargs) -> None:
        super().__init__(initial="git-view", **kwargs)
        self._repo = repo

    def compose(self) -> ComposeResult:
        yield GitView(self._repo, id="git-view")
        yield FileView(id="file-view")
        yield RGrepView(self._repo, id="rgrep-view")

    @property
    def file_view(self) -> FileView:
        return self.query_one("#file-view", FileView)

    @property
    def git_view(self) -> GitView:
        return self.query_one("#git-view", GitView)

    @property
    def rgrep_view(self) -> RGrepView:
        return self.query_one("#rgrep-view", RGrepView)

    def show_file(self, path: Path, *, line: int | None = None) -> None:
        self.file_view.open_path(path, line=line)
        self.current = "file-view"

    def show_git(self) -> None:
        self.current = "git-view"

    def show_rgrep(self) -> None:
        self.current = "rgrep-view"

    @property
    def showing_file(self) -> bool:
        return self.current == "file-view"
