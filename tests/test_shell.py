"""The lightweight in-center command runner."""

from pathlib import Path

import pytest

from tuuuui.app import TuuuuiApp
from tuuuui.widgets.center import Center


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "hello.py").write_text("print('hi')\n")
    return tmp_path


def _log_text(rich_log) -> str:
    return "\n".join(strip.text for strip in rich_log.lines)


async def test_shell_runs_command_and_shows_output(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        center = app.query_one(Center)
        center.show_shell()
        await pilot.pause()
        sv = center.shell_view
        sv.input.focus()
        sv.input.value = "echo hello-shell"
        await pilot.press("enter")
        for _ in range(40):
            await pilot.pause()
            if "hello-shell" in _log_text(sv.log):
                break
        text = _log_text(sv.log)
        assert "$ echo hello-shell" in text  # the command is echoed
        assert "hello-shell" in text  # ...and its output captured


async def test_shell_runs_in_app_root(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        center = app.query_one(Center)
        center.show_shell()
        await pilot.pause()
        sv = center.shell_view
        sv.input.focus()
        sv.input.value = "ls"
        await pilot.press("enter")
        for _ in range(40):
            await pilot.pause()
            if "hello.py" in _log_text(sv.log):
                break
        assert "hello.py" in _log_text(sv.log)


async def test_shell_history_navigation(project: Path):
    app = TuuuuiApp(project)
    async with app.run_test() as pilot:
        center = app.query_one(Center)
        center.show_shell()
        await pilot.pause()
        sv = center.shell_view
        sv._history = ["first", "second"]

        sv.history_prev()
        assert sv.input.value == "second"
        sv.history_prev()
        assert sv.input.value == "first"
        sv.history_prev()  # clamps at oldest
        assert sv.input.value == "first"

        sv.history_next()
        assert sv.input.value == "second"
        sv.history_next()  # past newest -> fresh prompt
        assert sv.input.value == ""
