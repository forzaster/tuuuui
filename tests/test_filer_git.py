"""Filer git-awareness: mark changed files + filter to changed only."""

import subprocess
from pathlib import Path

import pytest

from tuuuui.app import TuuuuiApp
from tuuuui.widgets.filer import Filer, FilerPanel
from tuuuui.widgets.git_view import GitView


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t.local")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.txt").write_text("1\n")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-qm", "first")
    (tmp_path / "a.txt").write_text("2\n")
    (tmp_path / "b.txt").write_text("x\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "second")
    # Leave an unstaged change.
    (tmp_path / "a.txt").write_text("3\n")
    return tmp_path


async def _settle(pilot, n: int = 5):
    for _ in range(n):
        await pilot.pause()


# --------------------------------------------------------- unit: filter_paths
def test_filter_paths_keeps_changed_and_their_dirs(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "keep.py").write_text("")
    (tmp_path / "src" / "drop.py").write_text("")
    (tmp_path / "other").mkdir()
    (tmp_path / "other" / "x.py").write_text("")

    filer = Filer(str(tmp_path))
    filer._only_changed = True
    filer._changed = {(tmp_path / "src" / "keep.py").resolve()}

    children = [tmp_path / "src", tmp_path / "other",
                tmp_path / "src" / "keep.py", tmp_path / "src" / "drop.py"]
    kept = set(filer.filter_paths(children))
    assert tmp_path / "src" in kept              # dir contains a changed file
    assert tmp_path / "other" not in kept        # dir has no changed file
    assert tmp_path / "src" / "keep.py" in kept
    assert tmp_path / "src" / "drop.py" not in kept


def test_filter_paths_passthrough_when_disabled(tmp_path: Path):
    filer = Filer(str(tmp_path))
    filer._only_changed = False
    children = [tmp_path / "a", tmp_path / "b"]
    assert list(filer.filter_paths(children)) == children


# ---------------------------------------------------- integration: marking
async def test_unstaged_changes_marked_in_filer(repo: Path):
    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await _settle(pilot)
        filer = app.query_one(Filer)
        assert (repo / "a.txt").resolve() in filer._changed
        assert (repo / "b.txt").resolve() not in filer._changed


async def test_selecting_commit_marks_its_files(repo: Path):
    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await _settle(pilot)
        gv = app.query_one(GitView)
        # The newest commit ("second") touched a.txt and b.txt.
        await gv._show_commit(gv._commits[0].sha)
        await _settle(pilot)
        filer = app.query_one(Filer)
        assert (repo / "a.txt").resolve() in filer._changed
        assert (repo / "b.txt").resolve() in filer._changed


# ------------------------------------------------------- integration: filter
async def test_checkbox_enables_filter(repo: Path):
    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await _settle(pilot)
        await pilot.click("#only-changed")
        await pilot.pause()
        assert app.query_one(Filer)._only_changed is True


async def test_filtered_tree_shows_only_changed(repo: Path):
    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await _settle(pilot)
        filer = app.query_one(Filer)
        app.query_one(FilerPanel).tree.set_only_changed(True)
        await _settle(pilot)
        # Only a.txt is unstaged-changed, so b.txt must be filtered out.
        visible = {node.data.path.name for node in filer._tree_nodes.values()
                   if node.data is not None and not node.data.path.is_dir()}
        assert "a.txt" in visible
        assert "b.txt" not in visible
