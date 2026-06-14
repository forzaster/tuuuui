"""Tab cycles the center pane between git view, editor, and shell."""

from pathlib import Path

import pytest

from tuuuui.app import TuuuuiApp
from tuuuui.widgets.center import Center


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "hello.py").write_text("print('hi')\n")
    return tmp_path


async def test_tab_cycles_git_and_shell_without_file(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        await pilot.pause()
        center = app.query_one(Center)
        assert center.current == "git-view"

        await pilot.press("tab")
        await pilot.pause()
        # No file open -> editor is skipped, so git -> shell.
        assert center.current == "shell-view"

        await pilot.press("tab")
        await pilot.pause()
        assert center.current == "git-view"


async def test_tab_cycles_through_editor_when_file_open(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(project / "hello.py")
        await pilot.pause()
        center = app.query_one(Center)
        assert center.current == "file-view"

        await pilot.press("tab")
        await pilot.pause()
        assert center.current == "shell-view"

        await pilot.press("tab")
        await pilot.pause()
        assert center.current == "git-view"

        await pilot.press("tab")
        await pilot.pause()
        assert center.current == "file-view"


async def test_tab_in_editor_switches_instead_of_typing(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        app._open_file(project / "hello.py")
        await pilot.pause()
        center = app.query_one(Center)
        before = center.file_view.editor.text
        # Focus is on the editor after opening; Tab must cycle, not insert.
        await pilot.press("tab")
        await pilot.pause()
        assert center.current == "shell-view"
        assert center.file_view.editor.text == before
