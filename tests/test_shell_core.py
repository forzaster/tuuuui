"""core.shell.run_command — the UI-independent command runner."""

from pathlib import Path

from tuuuui.core.shell import run_command


async def test_run_command_captures_stdout(tmp_path: Path):
    out, rc = await run_command("echo hi", tmp_path)
    assert out.strip() == "hi"
    assert rc == 0


async def test_run_command_captures_stderr_and_returncode(tmp_path: Path):
    out, rc = await run_command("echo oops 1>&2; exit 3", tmp_path)
    assert "oops" in out
    assert rc == 3


async def test_run_command_uses_cwd(tmp_path: Path):
    (tmp_path / "marker.txt").write_text("x")
    out, rc = await run_command("ls", tmp_path)
    assert "marker.txt" in out
    assert rc == 0
