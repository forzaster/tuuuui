"""C-n / C-p navigation in the list-style views (git log + buffer switcher)."""

import subprocess
from pathlib import Path

import pytest

from tuuuui.app import TuuuuiApp
from tuuuui.widgets.git_view import GitView


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t.local")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.py").write_text("one\n")
    _git(tmp_path, "add", "a.py")
    _git(tmp_path, "commit", "-qm", "first")
    (tmp_path / "b.py").write_text("two\n")
    return tmp_path


async def test_git_log_ctrl_n_p_moves_highlight(repo: Path):
    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        await pilot.pause()
        log = app.query_one(GitView).query_one("#log")
        log.focus()
        log.highlighted = 0
        await pilot.pause()

        await pilot.press("ctrl+n")
        await pilot.pause()
        assert log.highlighted == 1

        await pilot.press("ctrl+p")
        await pilot.pause()
        assert log.highlighted == 0


async def test_buffer_list_ctrl_n_moves_highlight(repo: Path):
    app = TuuuuiApp(repo)
    async with app.run_test() as pilot:
        app._open_file(repo / "a.py")
        await pilot.pause()
        app._open_file(repo / "b.py")
        await pilot.pause()

        await pilot.press("ctrl+x", "b")
        await pilot.pause()
        ol = app.screen.query_one("#buffers")
        ol.highlighted = 0
        await pilot.pause()

        await pilot.press("ctrl+n")
        await pilot.pause()
        assert ol.highlighted == 1
