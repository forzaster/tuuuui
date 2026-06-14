"""Async git helpers.

Thin wrappers around the ``git`` CLI. Every function runs git in a subprocess
and returns plain Python data, so they are easy to unit test and never touch the
UI. All functions raise :class:`GitError` on failure (non-zero exit or missing
git/repo); callers decide how to present that.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path


class GitError(Exception):
    """Raised when a git command fails or git/the repo is unavailable."""


@dataclass(frozen=True)
class Commit:
    """One line of ``git log``."""

    sha: str
    short_sha: str
    subject: str
    author: str
    date: str  # short relative date, e.g. "3 days ago"

    def one_line(self) -> str:
        return f"{self.short_sha}  {self.date:<14}  {self.author:<16}  {self.subject}"


async def _run_git(cwd: Path, *args: str) -> str:
    """Run ``git *args`` in *cwd*, returning stdout. Raise GitError on failure."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:  # git not installed
        raise GitError("git is not installed or not on PATH") from exc

    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        msg = stderr.decode("utf-8", "replace").strip() or "git command failed"
        raise GitError(msg)
    return stdout.decode("utf-8", "replace")


async def repo_root(cwd: Path) -> Path:
    """Return the repository root containing *cwd*, or raise GitError."""
    out = await _run_git(cwd, "rev-parse", "--show-toplevel")
    return Path(out.strip())


async def is_repo(cwd: Path) -> bool:
    """True if *cwd* is inside a git work tree."""
    try:
        out = await _run_git(cwd, "rev-parse", "--is-inside-work-tree")
    except GitError:
        return False
    return out.strip() == "true"


# Field separator unlikely to appear in commit metadata.
_SEP = "\x1f"
_LOG_FORMAT = _SEP.join(["%H", "%h", "%s", "%an", "%cr"])


async def log(cwd: Path, max_count: int = 500) -> list[Commit]:
    """Return up to *max_count* commits, newest first."""
    out = await _run_git(
        cwd,
        "log",
        f"--max-count={max_count}",
        f"--pretty=format:{_LOG_FORMAT}",
    )
    commits: list[Commit] = []
    for line in out.splitlines():
        if not line:
            continue
        parts = line.split(_SEP)
        if len(parts) != 5:
            continue
        sha, short, subject, author, date = parts
        commits.append(Commit(sha, short, subject, author, date))
    return commits


async def diff_unstaged(cwd: Path) -> str:
    """Working-tree diff (unstaged changes). May be empty."""
    return await _run_git(cwd, "diff")


async def show(cwd: Path, sha: str) -> str:
    """Diff introduced by commit *sha*."""
    return await _run_git(cwd, "show", "--patch", "--stat", sha)


def changed_paths_from_diff(diff: str) -> list[str]:
    """Extract the repo-relative file paths touched by a unified *diff*.

    Reads the ``diff --git a/<path> b/<path>`` headers, returning the post-image
    (``b/``) path for each. Deleted files (``b/dev/null``) are skipped. Paths are
    relative to the repository root. Order is preserved, duplicates removed.
    """
    seen: dict[str, None] = {}
    for line in diff.splitlines():
        if not line.startswith("diff --git "):
            continue
        marker = line.find(" b/")
        if marker == -1:
            continue
        path = line[marker + 3 :].strip()
        if not path or path == "dev/null":
            continue
        seen.setdefault(path, None)
    return list(seen)
