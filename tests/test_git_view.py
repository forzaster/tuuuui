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
    from tuuuui.widgets.git_view import UNSTAGED_ID

    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await pilot.pause()
        gv = app.query_one(GitView)
        log = gv.query_one("#log")
        # 2 synthetic rows (Unstaged/Staged) + 1 commit.
        assert log.option_count == 3

        # A new commit lands while the view is open.
        (repo / "b.txt").write_text("two\n")
        _git(repo, "add", "b.txt")
        _git(repo, "commit", "-qm", "second")

        await gv._do_refresh_log()
        await pilot.pause()
        assert log.option_count == 4
        # The diff was NOT switched away from the unstaged view.
        assert gv._current_id == UNSTAGED_ID


async def test_auto_refresh_preserves_highlighted_commit(repo: Path):
    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await pilot.pause()
        gv = app.query_one(GitView)
        log = gv.query_one("#log")
        log.highlighted = 2  # the first commit (after the 2 synthetic rows)
        first_sha = gv._commits[0].sha

        (repo / "b.txt").write_text("two\n")
        _git(repo, "add", "b.txt")
        _git(repo, "commit", "-qm", "second")
        await gv._do_refresh_log()
        await pilot.pause()

        # Highlight still points at the same commit (now pushed down one row).
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


async def _settle(pilot, n=6):
    for _ in range(n):
        await pilot.pause()


async def test_list_has_unstaged_and_staged_rows(repo: Path):
    from tuuuui.widgets.git_view import STAGED_ID, UNSTAGED_ID

    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await _settle(pilot)
        log = app.query_one(GitView).query_one("#log")
        assert log.get_option_at_index(0).id == UNSTAGED_ID
        assert log.get_option_at_index(1).id == STAGED_ID


async def test_selecting_staged_row_shows_staged_diff(repo: Path):
    from tuuuui.widgets.git_view import STAGED_ID

    # Stage a new file; leave a separate unstaged change.
    (repo / "b.txt").write_text("new\n")
    _git(repo, "add", "b.txt")
    (repo / "a.txt").write_text("one\nmod\n")

    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await _settle(pilot)
        gv = app.query_one(GitView)
        log = gv.query_one("#log")
        log.highlighted = 1  # Staged row
        await _settle(pilot)
        assert gv._current_id == STAGED_ID
        assert "b.txt" in gv.diff_text and "+new" in gv.diff_text
        assert "a.txt" not in gv.diff_text  # unstaged change not shown here


async def test_staged_row_marks_staged_files_in_filer(repo: Path):
    from tuuuui.widgets.filer import Filer

    (repo / "b.txt").write_text("new\n")
    _git(repo, "add", "b.txt")
    (repo / "a.txt").write_text("one\nmod\n")

    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await _settle(pilot)
        gv = app.query_one(GitView)
        gv.query_one("#log").highlighted = 1  # Staged
        await _settle(pilot)
        changed = app.query_one(Filer)._changed
        assert (repo / "b.txt").resolve() in changed       # staged
        assert (repo / "a.txt").resolve() not in changed    # only unstaged


async def test_switching_back_to_unstaged_row(repo: Path):
    from tuuuui.widgets.git_view import UNSTAGED_ID

    (repo / "a.txt").write_text("one\nmod\n")

    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await _settle(pilot)
        gv = app.query_one(GitView)
        log = gv.query_one("#log")
        log.highlighted = 1  # Staged
        await _settle(pilot)
        log.highlighted = 0  # back to Unstaged
        await _settle(pilot)
        assert gv._current_id == UNSTAGED_ID
        assert "+mod" in gv.diff_text


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
