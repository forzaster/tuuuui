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


def _add_commits(repo: Path, n: int, start: int = 0) -> None:
    for i in range(start, start + n):
        (repo / f"f{i}.txt").write_text(f"{i}\n")
        _git(repo, "add", f"f{i}.txt")
        _git(repo, "commit", "-qm", f"commit {i}")


async def test_first_page_is_capped_with_more_row(repo: Path):
    from tuuuui.widgets.git_view import MORE_ID, PAGE_SIZE

    # repo starts with 1 commit; add enough to exceed one page.
    _add_commits(repo, PAGE_SIZE + 5)

    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await _settle(pilot)
        gv = app.query_one(GitView)
        log = gv.query_one("#log")
        # Only one page of commits is loaded.
        assert len(gv._commits) == PAGE_SIZE
        assert gv._has_more is True
        # 2 synthetic rows + PAGE_SIZE commits + 1 MORE row.
        assert log.option_count == PAGE_SIZE + 3
        assert log.get_option_at_index(log.option_count - 1).id == MORE_ID


async def test_load_more_appends_next_page(repo: Path):
    from tuuuui.widgets.git_view import MORE_ID, PAGE_SIZE

    _add_commits(repo, PAGE_SIZE + 5)  # 1 + PAGE_SIZE + 5 commits total

    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await _settle(pilot)
        gv = app.query_one(GitView)
        log = gv.query_one("#log")

        await gv._do_load_more()
        await _settle(pilot)

        # All remaining commits are now loaded; no more MORE row.
        assert len(gv._commits) == PAGE_SIZE + 6
        assert gv._has_more is False
        assert log.get_option_at_index(log.option_count - 1).id != MORE_ID


async def test_no_more_row_when_history_fits_one_page(repo: Path):
    from tuuuui.widgets.git_view import MORE_ID, PAGE_SIZE

    _add_commits(repo, 3)  # well under a page

    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await _settle(pilot)
        gv = app.query_one(GitView)
        log = gv.query_one("#log")
        assert gv._has_more is False
        ids = [log.get_option_at_index(i).id for i in range(log.option_count)]
        assert MORE_ID not in ids
        assert len(gv._commits) == 4  # 1 initial + 3 added


async def test_selecting_more_row_loads_next_page(repo: Path):
    from tuuuui.widgets.git_view import MORE_ID, PAGE_SIZE

    _add_commits(repo, PAGE_SIZE + 5)

    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await _settle(pilot)
        gv = app.query_one(GitView)
        log = gv.query_one("#log")
        # Highlight the MORE row and activate it (Enter -> OptionSelected).
        log.focus()
        log.highlighted = log.option_count - 1
        assert log.get_option_at_index(log.highlighted).id == MORE_ID
        await pilot.press("enter")
        await _settle(pilot)
        assert len(gv._commits) == PAGE_SIZE + 6
        assert gv._has_more is False
