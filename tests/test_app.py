"""Smoke / integration tests driving the app with Textual's pilot."""

from pathlib import Path

import pytest

from tuuuui.app import TuuuuiApp
from tuuuui.widgets.center import Center
from tuuuui.widgets.file_view import FileView


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "hello.py").write_text("print('hi')\n")
    (tmp_path / "notes.md").write_text("# Title\n\nbody\n")
    return tmp_path


async def test_app_boots_with_git_view(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        center = app.query_one(Center)
        assert center.current == "git-view"
        await pilot.pause()


async def test_opening_file_switches_to_file_view(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(project / "hello.py")
        await pilot.pause()
        center = app.query_one(Center)
        assert center.current == "file-view"
        assert "print('hi')" in center.file_view.editor.text
        assert len(app.buffers) == 1


async def test_cx_g_returns_to_git_view(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(project / "hello.py")
        await pilot.pause()
        await pilot.press("ctrl+x", "g")
        await pilot.pause()
        assert app.query_one(Center).current == "git-view"


async def test_markdown_toggle(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(project / "notes.md")
        await pilot.pause()
        fv = app.query_one(FileView)
        assert fv.can_toggle_markdown()
        rendered = fv.toggle_markdown()
        assert rendered is True


async def test_cx_b_with_no_buffers_warns(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        await pilot.press("ctrl+x", "b")
        await pilot.pause()
        # No modal pushed when there are no buffers.
        assert app.screen_stack[-1] is app.screen
