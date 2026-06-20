"""Center pane (file mode): view/edit a file.

A :class:`FileView` holds two stacked views and flips between them with a
:class:`~textual.widgets.ContentSwitcher`:

* an :class:`Editor` (a ``TextArea`` with syntax highlighting), and
* a rendered :class:`~textual.widgets.Markdown` view (used for ``.md`` files).

Markdown files can toggle between raw editing and the rendered view. Editing
(emacs keybindings) is layered onto :class:`Editor` in Phase 3; for now the
editor is read-only.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import ContentSwitcher, Markdown
from textual.widgets.text_area import LanguageDoesNotExist

from .emacs import EmacsTextArea

# Map file extensions to tree-sitter language names bundled with Textual.
_EXT_LANG = {
    ".py": "python",
    ".md": "markdown",
    ".markdown": "markdown",
    ".json": "json",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".html": "html",
    ".css": "css",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".sh": "bash",
    ".bash": "bash",
    ".sql": "sql",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".xml": "xml",
}

_MAX_BYTES = 2_000_000  # don't try to load enormous files


def language_for(path: Path) -> str | None:
    """Return the tree-sitter language name for *path*, or None."""
    return _EXT_LANG.get(path.suffix.lower())


def _read_text(path: Path) -> tuple[str, bool]:
    """Return (text, is_error). Handles binary/oversized/unreadable files."""
    try:
        if path.stat().st_size > _MAX_BYTES:
            return (f"[file too large to display: {path}]", True)
        data = path.read_bytes()
    except OSError as exc:
        return (f"[could not read {path}: {exc}]", True)
    if b"\x00" in data:
        return (f"[binary file not shown: {path}]", True)
    return (data.decode("utf-8", "replace"), False)


class Editor(EmacsTextArea):
    """Syntax-highlighting text editor with emacs keybindings."""

    def load(self, path: Path, text: str, *, read_only: bool) -> None:
        self.read_only = read_only
        self.load_text(text)
        self.move_cursor((0, 0))
        try:
            self.language = language_for(path)
        except LanguageDoesNotExist:
            self.language = None

    @property
    def is_markdown(self) -> bool:
        return self.language == "markdown"


class FileView(Container):
    """Switches between a raw editor and a rendered markdown view."""

    DEFAULT_CSS = """
    FileView { height: 1fr; }
    FileView Editor { height: 1fr; }
    FileView Markdown { height: 1fr; padding: 0 1; }
    """

    def __init__(self, *, read_only: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._force_read_only = read_only
        self._path: Path | None = None
        # Text as last loaded or saved; used to detect unsaved edits.
        self._clean_text: str = ""

    def compose(self) -> ComposeResult:
        with ContentSwitcher(initial="editor"):
            yield Editor(id="editor", show_line_numbers=True)
            yield Markdown(id="rendered")

    @property
    def editor(self) -> Editor:
        return self.query_one("#editor", Editor)

    @property
    def path(self) -> Path | None:
        return self._path

    def open_path(self, path: Path) -> None:
        """Load *path* into the editor (raw view). Binary/unreadable -> read-only."""
        self._path = path
        text, is_error = _read_text(path)
        read_only = self._force_read_only or is_error
        self.editor.load(path, text, read_only=read_only)
        # Snapshot what the editor actually holds (post any normalization).
        self._clean_text = self.editor.text
        self.query_one(ContentSwitcher).current = "editor"

    def reload(self) -> None:
        """Re-read the open file from disk, keeping the cursor where possible.

        Refuses when the buffer has unsaved edits so an external change never
        silently discards the user's work (callers should check first).
        """
        if self._path is None or self.is_modified:
            return
        cursor = self.editor.cursor_location
        self.open_path(self._path)
        try:
            self.editor.move_cursor(cursor)
        except Exception:
            pass

    @property
    def read_only(self) -> bool:
        return self.editor.read_only

    @property
    def is_modified(self) -> bool:
        """True if the buffer is editable and differs from the saved file."""
        if self._path is None or self.editor.read_only:
            return False
        return self.editor.text != self._clean_text

    def save(self) -> Path:
        """Write the editor contents back to the file atomically. Returns the path."""
        if self._path is None:
            raise RuntimeError("no file open")
        if self.editor.read_only:
            raise RuntimeError("buffer is read-only")
        text = self.editor.text
        self._atomic_write(self._path, text)
        self._clean_text = text
        return self._path

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        """Write *text* to *path* via a temp file + os.replace (crash-safe).

        Preserves the original file's permission bits when it already exists.
        """
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.",
                                   suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
            try:
                os.chmod(tmp, os.stat(path).st_mode)  # keep original perms
            except OSError:
                pass
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def can_toggle_markdown(self) -> bool:
        return self._path is not None and self.editor.is_markdown

    def toggle_markdown(self) -> bool:
        """Flip raw editor <-> rendered markdown. Returns the new 'rendered' state."""
        if not self.can_toggle_markdown():
            return False
        switcher = self.query_one(ContentSwitcher)
        if switcher.current == "editor":
            self.query_one("#rendered", Markdown).update(self.editor.text)
            switcher.current = "rendered"
            return True
        switcher.current = "editor"
        return False
