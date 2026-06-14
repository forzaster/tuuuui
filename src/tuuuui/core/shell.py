"""Run a shell command and capture its output — UI-independent.

Kept in ``core`` alongside the other subprocess helpers (git, tmux) so the
widget layer stays free of process plumbing. Non-interactive by design: the
command runs to completion and its combined stdout/stderr is returned as text.
"""

from __future__ import annotations

import asyncio
from pathlib import Path


async def run_command(cmd: str, cwd: Path) -> tuple[str, int]:
    """Run *cmd* through the shell in *cwd*.

    Returns ``(combined_output, returncode)``. Raises :class:`OSError` if the
    process cannot be spawned.
    """
    proc = await asyncio.create_subprocess_shell(
        cmd,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    return out.decode("utf-8", "replace"), proc.returncode or 0
