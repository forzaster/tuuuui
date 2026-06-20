"""Center pane (git mode): a source list over a diff.

Top: a selectable list whose first two rows are the working-tree **Unstaged** and
**Staged** changes, followed by one line per commit (`git log`). The commit part
**auto-refreshes** on an interval so new commits appear without interaction; the
highlighted row and scroll position are preserved across refreshes.

Bottom: the diff for the highlighted row — unstaged diff, staged diff, or the
selected commit's diff. The diff does **not** auto-poll — press the reload button
or ``C-r`` to re-fetch the currently shown diff (handy while you edit files).

Whatever diff is shown also drives the filer: its files are marked / filtered via
the :class:`GitView.FilesChanged` message.
"""

from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, OptionList, Static
from textual.widgets.option_list import Option

from ..core import git
from .emacs_list import EmacsOptionList

# How often to poll `git log` for new commits.
LOG_REFRESH_SECONDS = 5.0

# How often to re-fetch the working-tree diff so external edits show up without
# a manual reload. The diff is only re-rendered when it actually changed.
WORKTREE_REFRESH_SECONDS = 2.0

# Synthetic row ids for the working-tree entries at the top of the list.
UNSTAGED_ID = "__unstaged__"
STAGED_ID = "__staged__"

# Style for the branch-base row (the commit `origin/develop` points to).
BASE_STYLE = "bold magenta"
BASE_MARKER = "◆"


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
    """Top commit log (auto-refresh) + bottom diff (manual reload)."""

    BINDINGS = [
        Binding("ctrl+r", "reload_diff", "Reload diff", show=True),
    ]

    class FilesChanged(Message):
        """Posted when the shown diff changes; carries the touched file paths.

        Paths are absolute. An empty set means the current diff touches nothing
        (e.g. a clean working tree).
        """

        def __init__(self, paths: set[Path]) -> None:
            self.paths = paths
            super().__init__()

    DEFAULT_CSS = """
    GitView { height: 1fr; }
    GitView #log { height: 40%; border-bottom: solid $accent; }
    GitView #diff-header {
        height: 1; background: $panel; padding: 0 1;
    }
    GitView #diff-title { width: 1fr; content-align: left middle; }
    GitView #reload-diff { min-width: 14; height: 1; border: none; }
    GitView #diff-scroll { height: 1fr; }
    GitView #diff { padding: 0 1; }
    """

    def __init__(self, repo: Path, *, poll_worktree: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._repo = repo
        self._poll_worktree = poll_worktree
        self._root: Path | None = None  # repository root (for absolute paths)
        self._commits: list[git.Commit] = []
        # Id of the row whose diff is currently shown: UNSTAGED_ID, STAGED_ID,
        # or a commit sha. Used to re-fetch on reload.
        self._current_id: str = UNSTAGED_ID
        # Suppress the highlight->diff reaction during programmatic log refresh.
        self._suppress_highlight = False
        # Plain text of the diff currently shown (for inspection/tests).
        self._diff_text = ""
        # Raw working-tree diff last rendered; lets the poller skip a re-render
        # when nothing changed (avoids flicker / scroll reset).
        self._last_worktree_diff: str | None = None
        # The branch base (e.g. "origin/develop") and the sha it points at, so
        # that commit row is marked. Both None when there's no remote default.
        self._base_label: str | None = None
        self._base_sha: str | None = None

    def _set_diff(self, renderable: Text) -> None:
        self._diff_text = renderable.plain
        self.query_one("#diff", Static).update(renderable)

    def _emit_changed(self, diff: str) -> None:
        """Broadcast the set of files touched by *diff* (absolute paths)."""
        root = self._root or self._repo
        paths = {(root / rel).resolve() for rel in git.changed_paths_from_diff(diff)}
        self.post_message(self.FilesChanged(paths))

    @property
    def diff_text(self) -> str:
        return self._diff_text

    def compose(self) -> ComposeResult:
        yield EmacsOptionList(id="log")
        with Horizontal(id="diff-header"):
            yield Static("Unstaged diff", id="diff-title")
            yield Button("⟳ Reload", id="reload-diff", variant="primary")
        with VerticalScroll(id="diff-scroll"):
            yield Static(id="diff")

    def on_mount(self) -> None:
        self.reload()
        self.set_interval(LOG_REFRESH_SECONDS, self._refresh_log)
        if self._poll_worktree:
            self.set_interval(WORKTREE_REFRESH_SECONDS, self._refresh_worktree_diff)

    # ----------------------------------------------------------------- full load
    def reload(self) -> None:
        self.run_worker(self._load(), group="git-load", exclusive=True)

    async def _load(self) -> None:
        log_widget = self.query_one("#log", OptionList)
        diff_widget = self.query_one("#diff", Static)
        if not await git.is_repo(self._repo):
            log_widget.clear_options()
            diff_widget.update(Text("Not a git repository.", style="dim"))
            self.post_message(self.FilesChanged(set()))
            return
        try:
            self._root = await git.repo_root(self._repo)
        except git.GitError:
            self._root = self._repo
        try:
            self._commits = await git.log(self._repo)
        except git.GitError as exc:
            self._set_diff(Text(f"git error: {exc}", style="red"))
            return
        await self._resolve_base()
        self._populate_log(self._commits)
        log_widget.highlighted = 0  # default to the Unstaged row
        await self._show_unstaged()

    async def _resolve_base(self) -> None:
        """Look up the branch base (origin/develop) and the commit it marks."""
        self._base_label = await git.base_ref(self._repo)
        self._base_sha = (
            await git.rev(self._repo, self._base_label) if self._base_label else None
        )

    def _commit_option(self, commit: git.Commit) -> Option:
        """Build a log row, highlighting the branch-base commit distinctly."""
        if self._base_sha is not None and commit.sha == self._base_sha:
            text = Text(f"{BASE_MARKER} {self._base_label}  ", style=BASE_STYLE)
            text.append(commit.one_line(), style="magenta")
            return Option(text, id=commit.sha)
        return Option(commit.one_line(), id=commit.sha)

    def _populate_log(self, commits: list[git.Commit]) -> None:
        log_widget = self.query_one("#log", OptionList)
        log_widget.clear_options()
        options = [
            Option(Text("● Unstaged changes", style="yellow"), id=UNSTAGED_ID),
            Option(Text("● Staged changes", style="green"), id=STAGED_ID),
            *(self._commit_option(c) for c in commits),
        ]
        log_widget.add_options(options)

    def _option_ids(self) -> list[str]:
        """All row ids in display order (synthetic rows first, then commits)."""
        return [UNSTAGED_ID, STAGED_ID, *(c.sha for c in self._commits)]

    # ------------------------------------------------------ periodic log refresh
    def _refresh_log(self) -> None:
        self.run_worker(self._do_refresh_log(), group="git-log", exclusive=True)

    async def _do_refresh_log(self) -> None:
        if not await git.is_repo(self._repo):
            return
        try:
            commits = await git.log(self._repo)
        except git.GitError:
            return
        if [c.sha for c in commits] == [c.sha for c in self._commits]:
            return  # nothing changed
        self._commits = commits
        log_widget = self.query_one("#log", OptionList)
        # Remember which row was highlighted (commit sha or synthetic id).
        kept_id: str | None = None
        if log_widget.highlighted is not None:
            try:
                kept_id = log_widget.get_option_at_index(log_widget.highlighted).id
            except Exception:
                kept_id = None
        # Repopulate without letting the highlight change reload the diff.
        self._suppress_highlight = True
        try:
            self._populate_log(commits)
            ids = self._option_ids()
            if kept_id in ids:
                log_widget.highlighted = ids.index(kept_id)
        finally:
            self._suppress_highlight = False

    # ------------------------------------------------ periodic worktree refresh
    def _refresh_worktree_diff(self) -> None:
        """Poll the working-tree diff so external edits show without a reload."""
        if self._current_id not in (UNSTAGED_ID, STAGED_ID):
            return  # a commit diff is immutable; nothing to poll
        self.run_worker(
            self._do_refresh_worktree_diff(), group="git-diff-poll", exclusive=True
        )

    async def _do_refresh_worktree_diff(self) -> None:
        if self._current_id not in (UNSTAGED_ID, STAGED_ID):
            return
        staged = self._current_id == STAGED_ID
        fetch = git.diff_staged if staged else git.diff_unstaged
        try:
            diff = await fetch(self._repo)
        except git.GitError:
            return  # transient git error: keep the current diff shown
        if diff == self._last_worktree_diff:
            return  # unchanged: skip the re-render to avoid flicker
        self._render_worktree(diff, staged=staged)

    # --------------------------------------------------------------- diff loaders
    async def _show_worktree(self, *, staged: bool) -> None:
        self._current_id = STAGED_ID if staged else UNSTAGED_ID
        fetch = git.diff_staged if staged else git.diff_unstaged
        try:
            diff = await fetch(self._repo)
        except git.GitError as exc:
            self.query_one("#diff-title", Static).update(
                "Staged diff" if staged else "Unstaged diff"
            )
            self._set_diff(Text(f"git error: {exc}", style="red"))
            self._emit_changed("")
            return
        self._render_worktree(diff, staged=staged)

    def _render_worktree(self, diff: str, *, staged: bool) -> None:
        """Render a freshly fetched working-tree *diff* and broadcast its files."""
        self._last_worktree_diff = diff
        self.query_one("#diff-title", Static).update(
            "Staged diff" if staged else "Unstaged diff"
        )
        if diff.strip():
            self._set_diff(_colorize_diff(diff))
        else:
            empty = "No staged changes." if staged else "No unstaged changes."
            self._set_diff(Text(empty, style="dim"))
        self._emit_changed(diff)

    async def _show_unstaged(self) -> None:
        await self._show_worktree(staged=False)

    async def _show_staged(self) -> None:
        await self._show_worktree(staged=True)

    async def _show_commit(self, sha: str) -> None:
        self._current_id = sha
        self.query_one("#diff-title", Static).update(f"Commit {sha[:9]}")
        try:
            diff = await git.show(self._repo, sha)
        except git.GitError as exc:
            self._set_diff(Text(f"git error: {exc}", style="red"))
            self._emit_changed("")
            return
        self._set_diff(_colorize_diff(diff))
        self._emit_changed(diff)

    # -------------------------------------------------------------------- events
    def _select(self, option_id: str | None) -> None:
        """Show the diff for the row *option_id* (synthetic id or commit sha)."""
        if option_id == UNSTAGED_ID:
            coro = self._show_unstaged()
        elif option_id == STAGED_ID:
            coro = self._show_staged()
        elif option_id:
            coro = self._show_commit(option_id)
        else:
            return
        self.run_worker(coro, group="git-diff", exclusive=True)

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        if event.option_list.id != "log" or self._suppress_highlight:
            return
        self._select(event.option.id)

    def action_reload_diff(self) -> None:
        """Re-fetch the diff currently shown (unstaged / staged / commit)."""
        self._select(self._current_id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "reload-diff":
            event.stop()
            self.action_reload_diff()
