"""File-system watching (UI-independent infrastructure).

Wraps :func:`watchfiles.awatch` so the app can refresh the git view, the filer
highlights and the open file when an external tool (e.g. Claude Code) edits files
on disk. The pure :func:`resolve_changes` turns raw watchfiles events into a set
of resolved absolute paths; :func:`awatch_paths` is the thin async generator the
app drives as a background worker.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from pathlib import Path

from watchfiles import awatch

# Debounce window (ms): coalesce bursty multi-write operations into one refresh.
DEBOUNCE_MS = 200


def resolve_changes(changes: Iterable[tuple[object, str]]) -> set[Path]:
    """Collapse raw ``(Change, path)`` events into resolved absolute paths."""
    return {Path(raw).resolve() for _, raw in changes}


async def awatch_paths(root: Path, **kwargs) -> AsyncIterator[set[Path]]:
    """Yield a set of changed absolute paths per debounced batch under *root*."""
    kwargs.setdefault("debounce", DEBOUNCE_MS)
    async for changes in awatch(root, **kwargs):
        yield resolve_changes(changes)
