"""Left pane: a scrollable file tree with git-change awareness.

:class:`Filer` is the tree itself (built on Textual's ``DirectoryTree``). It can
mark files that appear in the currently shown git diff (a ``*`` marker + color)
and, when asked, filter the tree down to only those changed files.

:class:`FilerPanel` wraps the tree with a "changed only" checkbox and is what the
app mounts as the left pane.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Checkbox, DirectoryTree


class Filer(DirectoryTree):
    """File-system tree for the left pane.

    Emacs navigation on top of the arrows: ``C-n``/``C-p`` (down/up),
    ``C-f``/``C-b`` (next/parent), ``C-v``/``M-v`` (page).
    """

    BINDINGS = [
        Binding("ctrl+n", "cursor_down", "Down", show=False),
        Binding("ctrl+p", "cursor_up", "Up", show=False),
        Binding("ctrl+f", "cursor_next_sibling", "Next", show=False),
        Binding("ctrl+b", "cursor_parent", "Parent", show=False),
        Binding("ctrl+v", "page_down", "Page down", show=False),
        Binding("alt+v", "page_up", "Page up", show=False),
    ]

    class FileOpened(Message):
        """Posted when the user selects a file in the tree."""

        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._changed: set[Path] = set()
        self._only_changed = False

    # --------------------------------------------------------- change awareness
    def set_changed_files(self, paths: set[Path]) -> None:
        """Set the files to mark as changed (absolute, resolved paths)."""
        self._changed = paths
        if self._only_changed:
            self.reload()  # re-apply the filter
        else:
            self._invalidate()  # repaint labels with markers

    def set_only_changed(self, only: bool) -> None:
        """Toggle filtering the tree to only changed files."""
        if only == self._only_changed:
            return
        self._only_changed = only
        self.reload()

    def _is_changed(self, path: Path) -> bool:
        return path.resolve() in self._changed

    def _contains_changed(self, directory: Path) -> bool:
        root = directory.resolve()
        return any(p == root or p.is_relative_to(root) for p in self._changed)

    # ----------------------------------------------------------- render / filter
    def render_label(self, node, base_style, style):  # type: ignore[override]
        label = super().render_label(node, base_style, style)
        data = node.data
        if data is not None and not data.path.is_dir() and self._is_changed(data.path):
            marked = Text.assemble(label, Text(" *", style="bold yellow"))
            marked.stylize("yellow")
            return marked
        return label

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        if not self._only_changed or not self._changed:
            return paths
        kept = []
        for path in paths:
            if path.is_dir():
                if self._contains_changed(path):
                    kept.append(path)
            elif self._is_changed(path):
                kept.append(path)
        return kept

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        event.stop()
        self.post_message(self.FileOpened(Path(event.path)))


class FilerPanel(Vertical):
    """Left pane: a "changed only" checkbox above the file tree."""

    DEFAULT_CSS = """
    FilerPanel { width: 26; min-width: 18; border-right: solid $accent; }
    FilerPanel #only-changed { height: 1; border: none; padding: 0 1; background: $panel; }
    FilerPanel Filer { height: 1fr; }
    """

    def __init__(self, root: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._root = root

    def compose(self) -> ComposeResult:
        yield Checkbox("Changed only", id="only-changed")
        yield Filer(str(self._root), id="filer-tree")

    @property
    def tree(self) -> Filer:
        return self.query_one(Filer)

    def set_changed_files(self, paths: set[Path]) -> None:
        self.tree.set_changed_files(paths)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "only-changed":
            event.stop()
            self.tree.set_only_changed(bool(event.value))
