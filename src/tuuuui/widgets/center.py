"""Center pane: swaps between the git view, the file view, and a shell.

Defaults to the git view ("while working"); opening a file from the filer
switches to the file view. ``C-x g`` switches back to git, and ``Tab`` cycles
git view -> editor -> shell (the editor is skipped when no file is open).
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.widgets import ContentSwitcher

from .file_view import FileView
from .git_view import GitView
from .shell import ShellView

GIT_VIEW = "git-view"
FILE_VIEW = "file-view"
SHELL_VIEW = "shell-view"


class Center(ContentSwitcher):
    """ContentSwitcher holding the git view, the file view, and the shell."""

    def __init__(self, repo: Path, **kwargs) -> None:
        super().__init__(initial=GIT_VIEW, **kwargs)
        self._repo = repo

    def compose(self) -> ComposeResult:
        yield GitView(self._repo, id=GIT_VIEW)
        yield FileView(id=FILE_VIEW)
        yield ShellView(self._repo, id=SHELL_VIEW)

    @property
    def file_view(self) -> FileView:
        return self.query_one(f"#{FILE_VIEW}", FileView)

    @property
    def git_view(self) -> GitView:
        return self.query_one(f"#{GIT_VIEW}", GitView)

    @property
    def shell_view(self) -> ShellView:
        return self.query_one(f"#{SHELL_VIEW}", ShellView)

    def show_file(self, path: Path) -> None:
        self.file_view.open_path(path)
        self.current = FILE_VIEW

    def show_git(self) -> None:
        self.current = GIT_VIEW

    def show_shell(self) -> None:
        self.current = SHELL_VIEW

    @property
    def showing_file(self) -> bool:
        return self.current == FILE_VIEW

    def cycle(self) -> str:
        """Advance to the next center mode and return its id.

        Order is git -> editor -> shell -> git; the editor is skipped while no
        file is open (its view would be empty).
        """
        order = [GIT_VIEW]
        if self.file_view.path is not None:
            order.append(FILE_VIEW)
        order.append(SHELL_VIEW)
        try:
            idx = order.index(self.current)
        except ValueError:
            idx = -1
        self.current = order[(idx + 1) % len(order)]
        return self.current
