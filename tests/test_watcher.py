"""Real-time file watching: change-set resolution + app refresh wiring."""

import subprocess
from pathlib import Path

import pytest
from watchfiles import Change

from tuuuui.app import TuuuuiApp
from tuuuui.core.watcher import resolve_changes
from tuuuui.widgets.filer import FilerPanel


# --------------------------------------------------- unit: resolve_changes
def test_resolve_changes_returns_resolved_absolute_paths(tmp_path: Path):
    f = tmp_path / "a.py"
    f.write_text("x")
    changes = {(Change.modified, str(f))}
    assert resolve_changes(changes) == {f.resolve()}


def test_resolve_changes_dedups_events_for_the_same_file(tmp_path: Path):
    f = tmp_path / "a.py"
    changes = {(Change.added, str(f)), (Change.modified, str(f))}
    assert resolve_changes(changes) == {f.resolve()}


# ----------------------------------------------------------- git/filer wiring
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
    return tmp_path


async def _settle(pilot, n: int = 6):
    for _ in range(n):
        await pilot.pause()


async def test_fs_change_marks_changed_file_in_filer(repo: Path):
    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await _settle(pilot)
        tree = app.query_one(FilerPanel).tree
        assert (repo / "a.txt").resolve() not in tree._changed  # clean so far

        # An external tool edits the file; the watcher reports it.
        (repo / "a.txt").write_text("changed\n")
        app._handle_fs_changes({(repo / "a.txt").resolve()})
        await _settle(pilot)

        assert (repo / "a.txt").resolve() in tree._changed


# ------------------------------------------------------- open-file reload
async def test_open_file_reloads_when_changed_externally(tmp_path: Path):
    f = tmp_path / "hello.py"
    f.write_text("print('hi')\n")
    app = TuuuuiApp(tmp_path)
    async with app.run_test() as pilot:
        app._open_file(f)
        await pilot.pause()
        # External edit + watcher event for this file.
        f.write_text("print('bye')\n")
        app._handle_fs_changes({f.resolve()})
        await pilot.pause()
        assert "print('bye')" in app.center.file_view.editor.text


async def test_open_file_with_unsaved_edits_is_not_clobbered(tmp_path: Path):
    f = tmp_path / "hello.py"
    f.write_text("print('hi')\n")
    app = TuuuuiApp(tmp_path)
    async with app.run_test() as pilot:
        app._open_file(f)
        await pilot.pause()
        # User has unsaved edits in the editor.
        editor = app.center.file_view.editor
        editor.text = "print('my unsaved work')\n"
        assert app.center.file_view.is_modified

        # The file also changes on disk; the watcher reports it.
        f.write_text("print('external')\n")
        app._handle_fs_changes({f.resolve()})
        await pilot.pause()

        # The user's unsaved edits must survive (no silent overwrite).
        assert "my unsaved work" in editor.text
