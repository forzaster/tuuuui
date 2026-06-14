"""GitView: auto log refresh + manual diff reload."""

import subprocess
from pathlib import Path

import pytest

from tuuuui.app import TuuuuiApp
from tuuuui.widgets.git_view import GitView


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t.local")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.txt").write_text("one\n")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-qm", "first")
    return tmp_path


async def test_log_auto_refresh_picks_up_new_commit(repo: Path):
    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await pilot.pause()
        gv = app.query_one(GitView)
        log = gv.query_one("#log")
        assert log.option_count == 1

        # A new commit lands while the view is open.
        (repo / "b.txt").write_text("two\n")
        _git(repo, "add", "b.txt")
        _git(repo, "commit", "-qm", "second")

        await gv._do_refresh_log()
        await pilot.pause()
        assert log.option_count == 2
        # The diff was NOT switched away from the unstaged view.
        assert gv._current_sha is None


async def test_auto_refresh_preserves_highlighted_commit(repo: Path):
    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await pilot.pause()
        gv = app.query_one(GitView)
        log = gv.query_one("#log")
        log.highlighted = 0
        first_sha = gv._commits[0].sha

        (repo / "b.txt").write_text("two\n")
        _git(repo, "add", "b.txt")
        _git(repo, "commit", "-qm", "second")
        await gv._do_refresh_log()
        await pilot.pause()

        # Highlight still points at the same commit (now at index 1).
        kept = log.get_option_at_index(log.highlighted).id
        assert kept == first_sha


async def test_manual_diff_reload_updates_unstaged(repo: Path):
    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await pilot.pause()
        gv = app.query_one(GitView)
        await gv._show_unstaged()
        assert "No unstaged changes" in gv.diff_text

        # Edit a tracked file, then reload the diff manually.
        (repo / "a.txt").write_text("one\nmore\n")
        gv.action_reload_diff()
        await pilot.pause()
        assert "+more" in gv.diff_text


async def test_reload_button_triggers_reload(repo: Path):
    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await pilot.pause()
        gv = app.query_one(GitView)
        await gv._show_unstaged()
        (repo / "a.txt").write_text("one\nbtn\n")
        await pilot.click("#reload-diff")
        await pilot.pause()
        assert "+btn" in gv.diff_text
