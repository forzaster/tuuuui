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

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container
from textual.document._document import Selection
from textual.widgets import ContentSwitcher, Markdown, TextArea
from textual.widgets.text_area import LanguageDoesNotExist

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


class Editor(TextArea):
    """Syntax-highlighting text editor. Emacs keys are added in Phase 3."""

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

    # Selection is needed by emacs kill/yank later; expose a clean reset.
    def reset_selection(self) -> None:
        self.selection = Selection.cursor(self.cursor_location)


class FileView(Container):
    """Switches between a raw editor and a rendered markdown view."""

    DEFAULT_CSS = """
    FileView { height: 1fr; }
    FileView Editor { height: 1fr; }
    FileView Markdown { height: 1fr; padding: 0 1; }
    """

    def __init__(self, *, read_only: bool = True, **kwargs) -> None:
        super().__init__(**kwargs)
        self._read_only = read_only
        self._path: Path | None = None

    def compose(self) -> ComposeResult:
        with ContentSwitcher(initial="editor"):
            yield Editor(id="editor", read_only=self._read_only, show_line_numbers=True)
            yield Markdown(id="rendered")

    @property
    def editor(self) -> Editor:
        return self.query_one("#editor", Editor)

    @property
    def path(self) -> Path | None:
        return self._path

    def open_path(self, path: Path) -> None:
        """Load *path* into the editor (raw view)."""
        self._path = path
        text, _is_error = _read_text(path)
        self.editor.load(path, text, read_only=self._read_only)
        self.query_one(ContentSwitcher).current = "editor"

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
