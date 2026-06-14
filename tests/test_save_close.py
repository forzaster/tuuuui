"""Atomic save, dirty tracking, and the unsaved-changes close guard."""

import os
import stat
from pathlib import Path

import pytest

from tuuuui.app import TuuuuiApp
from tuuuui.widgets.center import Center
from tuuuui.widgets.confirm import ConfirmScreen


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "a.py").write_text("hello\n")
    return tmp_path


async def test_is_modified_tracks_edits_and_save(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(project / "a.py")
        await pilot.pause()
        fv = app.query_one(Center).file_view
        assert fv.is_modified is False

        fv.editor.focus()
        fv.editor.move_cursor((0, 0))
        await pilot.press("X")
        await pilot.pause()
        assert fv.is_modified is True

        await pilot.press("ctrl+x", "ctrl+s")
        await pilot.pause()
        assert fv.is_modified is False
        assert (project / "a.py").read_text().startswith("X")


async def test_atomic_save_preserves_permissions(project: Path):
    target = project / "a.py"
    os.chmod(target, 0o750)
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(target)
        await pilot.pause()
        fv = app.query_one(Center).file_view
        fv.editor.focus()
        fv.editor.move_cursor((0, 0))
        await pilot.press("Z")
        await pilot.press("ctrl+x", "ctrl+s")
        await pilot.pause()
        assert stat.S_IMODE(os.stat(target).st_mode) == 0o750
        assert target.read_text().startswith("Z")


async def test_close_unsaved_prompts_and_keeps_on_no(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(project / "a.py")
        await pilot.pause()
        fv = app.query_one(Center).file_view
        fv.editor.focus()
        fv.editor.move_cursor((0, 0))
        await pilot.press("Q")
        await pilot.pause()
        assert fv.is_modified is True

        await pilot.press("ctrl+x", "ctrl+c")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)

        await pilot.press("n")  # keep editing
        await pilot.pause()
        assert app.query_one(Center).current == "file-view"
        assert len(app.buffers) == 1


async def test_close_unsaved_discards_on_yes(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(project / "a.py")
        await pilot.pause()
        fv = app.query_one(Center).file_view
        fv.editor.focus()
        fv.editor.move_cursor((0, 0))
        await pilot.press("Q")
        await pilot.pause()

        await pilot.press("ctrl+x", "ctrl+c")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)

        await pilot.press("y")  # discard
        await pilot.pause()
        assert app.query_one(Center).current == "git-view"
        assert len(app.buffers) == 0
        # Discarded: the file on disk is untouched.
        assert (project / "a.py").read_text() == "hello\n"


async def test_close_without_changes_no_prompt(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(project / "a.py")
        await pilot.pause()
        await pilot.press("ctrl+x", "ctrl+c")
        await pilot.pause()
        assert not isinstance(app.screen, ConfirmScreen)
        assert app.query_one(Center).current == "git-view"
