"""Async recursive-grep helpers (ripgrep).

Thin wrapper around the ``rg`` CLI. ``search`` runs ripgrep in a subprocess and
returns plain Python data (a list of :class:`Match`), so it is easy to unit test
and never touches the UI. Failures raise :class:`RGrepError`; "no matches" is an
empty list, not an error.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path


class RGrepError(Exception):
    """Raised when ripgrep fails or is unavailable."""


@dataclass(frozen=True)
class Match:
    """One matching line found by ripgrep."""

    path: Path  # absolute path to the file
    line: int  # 1-based line number
    column: int  # 1-based column of the first submatch (1 if none)
    text: str  # the matching line, without the trailing newline

    def one_line(self, root: Path) -> str:
        """``relpath:line: text`` for display, relative to *root* when possible."""
        try:
            shown = self.path.relative_to(root)
        except ValueError:
            shown = self.path
        return f"{shown}:{self.line}: {self.text.strip()}"


# Cap how many matches we surface so a broad query can't flood the UI.
DEFAULT_MAX_RESULTS = 1000


async def search(
    root: Path,
    pattern: str,
    *,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> list[Match]:
    """Recursively search *root* for *pattern*, returning up to *max_results*.

    Uses ripgrep with smart-case matching (case-insensitive unless the pattern
    contains an uppercase letter). Respects ``.gitignore`` and skips binary
    files, mirroring ripgrep's defaults. An empty *pattern* yields no results.
    """
    if not pattern:
        return []
    try:
        proc = await asyncio.create_subprocess_exec(
            "rg",
            "--json",
            "--smart-case",
            "--",
            pattern,
            ".",
            cwd=str(root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:  # ripgrep not installed
        raise RGrepError("rg (ripgrep) is not installed or not on PATH") from exc

    stdout, stderr = await proc.communicate()
    # rg exit codes: 0 = matches, 1 = no matches, 2 = error.
    if proc.returncode not in (0, 1):
        msg = stderr.decode("utf-8", "replace").strip() or "rg command failed"
        raise RGrepError(msg)
    return _parse(stdout.decode("utf-8", "replace"), root, max_results)


def _parse(out: str, root: Path, max_results: int) -> list[Match]:
    """Parse ripgrep ``--json`` stream output into :class:`Match` objects."""
    matches: list[Match] = []
    for line in out.splitlines():
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "match":
            continue
        data = event.get("data", {})
        path_text = data.get("path", {}).get("text")
        if not path_text:
            continue  # path may be bytes (non-UTF8); skip such matches
        line_text = data.get("lines", {}).get("text", "")
        submatches = data.get("submatches", [])
        column = submatches[0]["start"] + 1 if submatches else 1
        matches.append(
            Match(
                path=(root / path_text).resolve(),
                line=data.get("line_number", 0),
                column=column,
                text=line_text.rstrip("\n"),
            )
        )
        if len(matches) >= max_results:
            break
    return matches
