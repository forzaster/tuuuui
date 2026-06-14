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
