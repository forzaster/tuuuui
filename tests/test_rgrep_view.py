"""RGrepView: search input -> result list -> open file at line (C-x r)."""

from pathlib import Path

import pytest

from tuuuui.app import TuuuuiApp
from tuuuui.widgets.center import Center
from tuuuui.widgets.rgrep_view import RGrepView


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "hello.py").write_text("print('hi')\nNEEDLE = 1\nprint('bye')\n")
    (tmp_path / "other.py").write_text("x = 0\nfind_needle()\n")
    return tmp_path


async def test_cx_r_shows_rgrep_and_focuses_input(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        await pilot.press("ctrl+x", "r")
        await pilot.pause()
        center = app.query_one(Center)
        assert center.current == "rgrep-view"
        assert app.focused is center.rgrep_view.input


async def test_search_populates_results(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        view = app.query_one(RGrepView)
        view.input.value = "needle"
        await pilot.pause()
        await view._search("needle")
        await pilot.pause()
        results = view.query_one("#rgrep-results")
        # NEEDLE (smart-case) in hello.py + needle in other.py.
        assert results.option_count == 2


async def test_selecting_result_opens_file_at_line(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        view = app.query_one(RGrepView)
        await view._search("NEEDLE")
        await pilot.pause()
        match = next(m for m in view._matches if m.path.name == "hello.py")
        view.post_message(RGrepView.OpenMatch(match.path, match.line))
        await pilot.pause()
        center = app.query_one(Center)
        assert center.current == "file-view"
        assert center.file_view.path == project / "hello.py"
        # Cursor on the matching line (0-based row == line - 1).
        assert center.file_view.editor.cursor_location[0] == match.line - 1


async def test_no_match_reports_status(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        view = app.query_one(RGrepView)
        await view._search("zzz-not-present")
        await pilot.pause()
        status = view.query_one("#rgrep-status")
        assert "0 match" in str(status.render())
