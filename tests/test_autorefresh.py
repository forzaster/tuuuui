"""Auto-refresh via polling (no watchfiles): worktree diff + open-file reload."""

import subprocess
from pathlib import Path

import pytest

from tuuuui.app import TuuuuiApp
from tuuuui.widgets.filer import FilerPanel
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


async def _settle(pilot, n: int = 6):
    for _ in range(n):
        await pilot.pause()


# ----------------------------------------------- git view / filer auto-refresh
async def test_worktree_diff_refresh_marks_file_in_filer(repo: Path):
    app = TuuuuiApp(repo, watch=True)
    async with app.run_test() as pilot:
        await _settle(pilot)
        gv = app.query_one(GitView)
        tree = app.query_one(FilerPanel).tree
        assert (repo / "a.txt").resolve() not in tree._changed  # clean

        # An external tool edits a tracked file; the next poll tick fires.
        (repo / "a.txt").write_text("changed\n")
        gv._refresh_worktree_diff()
        await _settle(pilot)

        assert (repo / "a.txt").resolve() in tree._changed
        assert "changed" in gv.diff_text


async def test_worktree_diff_refresh_skipped_for_commit_rows(repo: Path):
    # Make a second commit so a commit row exists and can be highlighted.
    (repo / "a.txt").write_text("two\n")
    _git(repo, "commit", "-aqm", "second")
    app = TuuuuiApp(repo, watch=True)
    async with app.run_test() as pilot:
        await _settle(pilot)
        gv = app.query_one(GitView)
        gv.query_one("#log").highlighted = 2  # first commit row
        await _settle(pilot)
        before = gv.diff_text

        # A working-tree edit must NOT disturb the shown commit diff.
        (repo / "a.txt").write_text("three\n")
        gv._refresh_worktree_diff()
        await _settle(pilot)
        assert gv.diff_text == before


# ----------------------------------------------------- open-file auto-reload
async def test_open_file_reloads_on_external_edit(tmp_path: Path):
    f = tmp_path / "hello.py"
    f.write_text("print('hi')\n")
    app = TuuuuiApp(tmp_path, watch=True)
    async with app.run_test() as pilot:
        app._open_file(f)
        await pilot.pause()
        f.write_text("print('bye')\n")
        app._poll_open_file()
        await pilot.pause()
        assert "print('bye')" in app.center.file_view.editor.text


async def test_open_file_with_unsaved_edits_is_not_clobbered(tmp_path: Path):
    f = tmp_path / "hello.py"
    f.write_text("print('hi')\n")
    app = TuuuuiApp(tmp_path, watch=True)
    async with app.run_test() as pilot:
        app._open_file(f)
        await pilot.pause()
        editor = app.center.file_view.editor
        editor.text = "print('my unsaved work')\n"
        assert app.center.file_view.is_modified

        f.write_text("print('external')\n")
        app._poll_open_file()
        await pilot.pause()
        assert "my unsaved work" in editor.text
