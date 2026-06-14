"""Buffer management for opened files (emacs ``C-x b`` style).

A buffer is just a file the user has opened. :class:`BufferManager` keeps them in
most-recently-used order so the switcher can offer the previous buffer first,
exactly like emacs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Buffer:
    """An opened file."""

    path: Path

    @property
    def name(self) -> str:
        return self.path.name


@dataclass
class BufferManager:
    """Ordered, de-duplicated set of opened buffers (most-recent first)."""

    _buffers: list[Buffer] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self._buffers)

    def __iter__(self):
        return iter(self._buffers)

    @property
    def buffers(self) -> list[Buffer]:
        """Buffers in most-recently-used order (a copy)."""
        return list(self._buffers)

    def open(self, path: Path) -> Buffer:
        """Record *path* as the current buffer, moving it to the front."""
        path = Path(path)
        for existing in self._buffers:
            if existing.path == path:
                self._buffers.remove(existing)
                self._buffers.insert(0, existing)
                return existing
        buf = Buffer(path)
        self._buffers.insert(0, buf)
        return buf

    @property
    def current(self) -> Buffer | None:
        """The most-recently opened buffer, if any."""
        return self._buffers[0] if self._buffers else None

    @property
    def previous(self) -> Buffer | None:
        """The buffer to switch to by default with ``C-x b`` (the 2nd MRU)."""
        return self._buffers[1] if len(self._buffers) > 1 else None

    def close(self, path: Path) -> None:
        """Forget the buffer for *path* if present."""
        path = Path(path)
        self._buffers = [b for b in self._buffers if b.path != path]
