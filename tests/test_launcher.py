"""Tests for the tuuuui-tmux launcher command construction."""

from tuuuui.launcher import tmux_setup_argv


def test_setup_argv_three_steps():
    cmds = tmux_setup_argv("tuuuui", "app-cmd", "claude", percent=30)
    assert len(cmds) == 3
    assert cmds[0] == ["tmux", "new-session", "-d", "-s", "tuuuui", "app-cmd"]
    assert cmds[1] == [
        "tmux", "split-window", "-h", "-d", "-l", "30%", "-t", "tuuuui", "claude",
    ]
    assert cmds[2] == ["tmux", "select-pane", "-L", "-t", "tuuuui"]


def test_setup_argv_custom_percent_and_session():
    cmds = tmux_setup_argv("dev", "app", "copilot", percent=40)
    assert cmds[0][-2:] == ["dev", "app"]
    assert "40%" in cmds[1]
    assert cmds[1][-1] == "copilot"
    assert cmds[2] == ["tmux", "select-pane", "-L", "-t", "dev"]
