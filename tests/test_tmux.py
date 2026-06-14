"""Phase 4: tmux workspace helpers."""

from tuuuui.core import tmux


def test_split_right_argv_detached_by_default():
    argv = tmux.split_right_argv("claude", percent=30)
    assert argv == ["tmux", "split-window", "-h", "-l", "30%", "-d", "claude"]


def test_split_right_argv_with_focus():
    argv = tmux.split_right_argv("copilot", percent=40, focus=True)
    assert argv == ["tmux", "split-window", "-h", "-l", "40%", "copilot"]


def test_spawn_outside_tmux_reports_error(monkeypatch):
    monkeypatch.delenv("TMUX", raising=False)
    ok, message = tmux.spawn_workspace("claude")
    assert ok is False
    assert "tmux" in message.lower()


def test_is_inside_tmux(monkeypatch):
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,123,0")
    assert tmux.is_inside_tmux() is True
    monkeypatch.delenv("TMUX")
    assert tmux.is_inside_tmux() is False


async def test_cx_t_spawns_workspace(tmp_path, monkeypatch):
    """C-x t calls the spawn helper and marks the workspace running on success."""
    from tuuuui.app import TuuuuiApp
    from tuuuui.core import tmux as tmux_mod
    from tuuuui.widgets.workspace import Workspace

    calls = []

    def fake_spawn(command, *a, **kw):
        calls.append(command)
        return (True, f"Workspace running: {command}")

    monkeypatch.setattr(tmux_mod, "spawn_workspace", fake_spawn)

    app = TuuuuiApp(tmp_path, workspace_cmd="claude")
    async with app.run_test() as pilot:
        await pilot.press("ctrl+x", "t")
        await pilot.pause()
        assert calls == ["claude"]
        assert app.query_one(Workspace).running is True
