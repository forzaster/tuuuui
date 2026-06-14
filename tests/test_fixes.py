"""Regression tests for: filer emacs nav, syntax highlighting, editor focus."""

from pathlib import Path

import pytest

from tuuuui.app import TuuuuiApp
from tuuuui.widgets.center import Center
from tuuuui.widgets.filer import Filer


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "a.py").write_text("import os\n\n\ndef foo():\n    return 1\n")
    (tmp_path / "b.py").write_text("x = 1\n")
    (tmp_path / "c.py").write_text("y = 2\n")
    return tmp_path


async def test_opening_file_focuses_editor(project: Path):
    """The core 'emacs keys don't work' fix: focus must move to the editor."""
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(project / "a.py")
        await pilot.pause()
        editor = app.query_one(Center).file_view.editor
        assert app.focused is editor


async def test_editor_keys_act_after_open(project: Path):
    """After opening, emacs keys reach the editor without manual focusing."""
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(project / "a.py")
        await pilot.pause()
        editor = app.query_one(Center).file_view.editor
        editor.move_cursor((0, 0))
        await pilot.press("ctrl+e")  # end of line "import os"
        await pilot.pause()
        assert editor.cursor_location == (0, 9)


async def test_syntax_highlighting_is_applied(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(project / "a.py")
        await pilot.pause()
        editor = app.query_one(Center).file_view.editor
        assert editor.language == "python"
        assert type(editor.document).__name__ == "SyntaxAwareDocument"
        highlights = editor._highlights
        assert sum(1 for v in highlights.values() if v) > 0


async def test_editor_undo(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(project / "b.py")
        await pilot.pause()
        editor = app.query_one(Center).file_view.editor
        original = editor.text
        editor.move_cursor((0, 0))
        await pilot.press("Q")  # insert a char
        await pilot.pause()
        assert editor.text != original
        await pilot.press("ctrl+underscore")  # undo (C-/ on most terminals)
        await pilot.pause()
        assert editor.text == original


async def test_close_file_returns_to_git_view(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(project / "a.py")
        await pilot.pause()
        assert app.query_one(Center).current == "file-view"
        assert len(app.buffers) == 1
        await pilot.press("ctrl+x", "ctrl+c")  # close file
        await pilot.pause()
        assert app.query_one(Center).current == "git-view"
        assert len(app.buffers) == 0  # buffer closed


async def test_only_two_panes(project: Path):
    """The right-hand workspace pane is gone; tmux provides it instead."""
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(app.query("#workspace")) == 0
        assert len(app.query("#filer")) == 1
        assert len(app.query("#center")) == 1


async def test_filer_ctrl_n_moves_down(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        filer = app.query_one(Filer)
        filer.focus()
        await pilot.pause()
        start = filer.cursor_line
        await pilot.press("ctrl+n")
        await pilot.pause()
        assert filer.cursor_line == start + 1
        await pilot.press("ctrl+p")
        await pilot.pause()
        assert filer.cursor_line == start
