"""Center pane (git mode): commit log over a diff.

Top:  one line per commit (`git log`), scrollable, selectable.
Bottom: a diff. Defaults to the unstaged working-tree diff; highlighting a commit
in the log swaps the bottom pane to that commit's diff.
"""

from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from ..core import git


def _colorize_diff(diff: str) -> Text:
    """Render a unified diff with added/removed/hunk colors."""
    text = Text()
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            style = "green"
        elif line.startswith("-") and not line.startswith("---"):
            style = "red"
        elif line.startswith("@@"):
            style = "cyan"
        elif line.startswith(("diff ", "index ", "+++", "---")):
            style = "bold yellow"
        else:
            style = ""
        text.append(line + "\n", style=style)
    return text


class GitView(Vertical):
    """Top commit log + bottom diff."""

    DEFAULT_CSS = """
    GitView { height: 1fr; }
    GitView #log { height: 40%; border-bottom: solid $accent; }
    GitView #diff-scroll { height: 1fr; }
    GitView #diff { padding: 0 1; }
    """

    def __init__(self, repo: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._repo = repo
        self._commits: list[git.Commit] = []

    def compose(self) -> ComposeResult:
        yield OptionList(id="log")
        with VerticalScroll(id="diff-scroll"):
            yield Static(id="diff")

    def on_mount(self) -> None:
        self.reload()

    def reload(self) -> None:
        self.run_worker(self._load(), exclusive=True)

    async def _load(self) -> None:
        log_widget = self.query_one("#log", OptionList)
        diff_widget = self.query_one("#diff", Static)
        if not await git.is_repo(self._repo):
            log_widget.clear_options()
            diff_widget.update(Text("Not a git repository.", style="dim"))
            return
        try:
            self._commits = await git.log(self._repo)
        except git.GitError as exc:
            diff_widget.update(Text(f"git error: {exc}", style="red"))
            return
        log_widget.clear_options()
        log_widget.add_options(
            [Option(c.one_line(), id=c.sha) for c in self._commits]
        )
        await self._show_unstaged()

    async def _show_unstaged(self) -> None:
        diff_widget = self.query_one("#diff", Static)
        try:
            diff = await git.diff_unstaged(self._repo)
        except git.GitError as exc:
            diff_widget.update(Text(f"git error: {exc}", style="red"))
            return
        if diff.strip():
            diff_widget.update(_colorize_diff(diff))
        else:
            diff_widget.update(Text("No unstaged changes.", style="dim"))

    async def _show_commit(self, sha: str) -> None:
        diff_widget = self.query_one("#diff", Static)
        try:
            diff = await git.show(self._repo, sha)
        except git.GitError as exc:
            diff_widget.update(Text(f"git error: {exc}", style="red"))
            return
        diff_widget.update(_colorize_diff(diff))

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        if event.option_list.id != "log":
            return
        sha = event.option.id
        if sha:
            self.run_worker(self._show_commit(sha), exclusive=True)
