"""Phase 3: emacs editing, kill-ring, save, and C-x chords from the editor."""

from pathlib import Path

import pytest

from tuuuui.app import TuuuuiApp
from tuuuui.widgets.center import Center
from tuuuui.widgets.emacs import EmacsTextArea


@pytest.fixture(autouse=True)
def _clear_kill_ring():
    EmacsTextArea._kill_ring.clear()
    yield
    EmacsTextArea._kill_ring.clear()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "a.py").write_text("hello\nworld\n")
    (tmp_path / "b.py").write_text("second\n")
    return tmp_path


async def _open(app, path):
    app._open_file(path)


async def test_file_is_editable(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        await _open(app, project / "a.py")
        await pilot.pause()
        editor = app.query_one(Center).file_view.editor
        assert editor.read_only is False
        editor.focus()
        await pilot.pause()
        await pilot.press("X")
        await pilot.pause()
        assert editor.text.startswith("X")


async def test_cx_save_writes_file(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        await _open(app, project / "a.py")
        await pilot.pause()
        editor = app.query_one(Center).file_view.editor
        editor.focus()
        await pilot.pause()
        await pilot.press("Z")  # insert at start
        await pilot.pause()
        await pilot.press("ctrl+x", "ctrl+s")
        await pilot.pause()
        assert (project / "a.py").read_text().startswith("Z")


async def test_cx_g_from_editor_focus(project: Path):
    """The C-x prefix must work even while the editor has focus."""
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        await _open(app, project / "a.py")
        await pilot.pause()
        editor = app.query_one(Center).file_view.editor
        editor.focus()
        await pilot.pause()
        await pilot.press("ctrl+x", "g")
        await pilot.pause()
        assert app.query_one(Center).current == "git-view"
        # The 'g' must NOT have been typed into the editor.
        assert "g" not in editor.text.split("\n")[0][:1]


async def test_cx_b_from_editor_opens_switcher(project: Path):
    from tuuuui.widgets.buffer_list import BufferList

    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        await _open(app, project / "a.py")
        await _open(app, project / "b.py")
        await pilot.pause()
        editor = app.query_one(Center).file_view.editor
        editor.focus()
        await pilot.pause()
        await pilot.press("ctrl+x", "b")
        await pilot.pause()
        assert isinstance(app.screen, BufferList)


async def test_kill_line_and_yank(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        await _open(app, project / "a.py")
        await pilot.pause()
        editor = app.query_one(Center).file_view.editor
        editor.focus()
        editor.move_cursor((0, 0))
        await pilot.pause()
        await pilot.press("ctrl+k")  # kill "hello"
        await pilot.pause()
        assert EmacsTextArea._kill_ring[0] == "hello"
        assert editor.text.startswith("\nworld")
        await pilot.press("ctrl+y")  # yank it back
        await pilot.pause()
        assert editor.text.startswith("hello\nworld")


async def test_set_mark_and_copy_region(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        await _open(app, project / "a.py")
        await pilot.pause()
        editor = app.query_one(Center).file_view.editor
        editor.focus()
        editor.move_cursor((0, 0))
        await pilot.pause()
        await pilot.press("ctrl+space")  # set mark at start
        editor.move_cursor((0, 5))  # select "hello"
        await pilot.pause()
        await pilot.press("alt+w")  # copy region
        await pilot.pause()
        assert EmacsTextArea._kill_ring[0] == "hello"
        # copy must not modify the buffer
        assert editor.text == "hello\nworld\n"


async def test_search_moves_cursor(project: Path):
    from tuuuui.widgets.search import SearchScreen

    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        await _open(app, project / "a.py")
        await pilot.pause()
        editor = app.query_one(Center).file_view.editor
        editor.focus()
        editor.move_cursor((0, 0))
        await pilot.pause()
        editor._search_forward("world")
        await pilot.pause()
        assert editor.cursor_location[0] == 1  # moved to line "world"
