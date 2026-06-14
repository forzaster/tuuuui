"""TuuuuiApp — the 3-pane terminal IDE.

Layout: [ Filer | Center (git view / file view) | Workspace ].

Emacs-style ``C-x`` is a *prefix*: press ``C-x`` then a second key. The app
tracks a pending-prefix state and interprets the next key as a chord:

* ``C-x b``     buffer switcher (recently opened files)
* ``C-x g``     show the git view
* ``C-x o``     cycle focus across panes
* ``C-x C-s``   save (Phase 3 — currently a no-op notice)
* ``C-x C-c``   quit

``F2`` toggles a Markdown file between raw editing and the rendered view.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static

from .core import tmux
from .core.buffers import BufferManager
from .widgets.buffer_list import BufferList
from .widgets.center import Center
from .widgets.filer import Filer
from .widgets.workspace import Workspace


class TuuuuiApp(App):
    """A 3-pane terminal IDE."""

    CSS_PATH = "app.tcss"
    TITLE = "tuuuui"

    BINDINGS = [
        Binding("ctrl+x", "cx_prefix", "C-x …", priority=True, show=True),
        Binding("f2", "toggle_markdown", "MD render", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]

    def __init__(
        self,
        root: Path | None = None,
        *,
        workspace_cmd: str | None = None,
        tmux_mode: bool = False,
    ) -> None:
        super().__init__()
        self.root = Path(root or Path.cwd()).resolve()
        self.workspace_cmd = workspace_cmd or tmux.DEFAULT_WORKSPACE_CMD
        self.tmux_mode = tmux_mode
        self.buffers = BufferManager()
        self._cx_pending = False
        self._cx_timer = None

    # ----------------------------------------------------------------- layout
    def compose(self) -> ComposeResult:
        yield Header()
        yield Filer(str(self.root), id="filer")
        yield Center(self.root, id="center")
        workspace = Workspace(id="workspace")
        workspace.command = self.workspace_cmd
        yield workspace
        yield Static("", id="prefix-hint")
        yield Footer()

    def on_mount(self) -> None:
        if self.tmux_mode:
            self.action_spawn_workspace()

    @property
    def center(self) -> Center:
        return self.query_one("#center", Center)

    # ------------------------------------------------------------ file opening
    def on_filer_file_opened(self, event: Filer.FileOpened) -> None:
        self._open_file(event.path)

    def _open_file(self, path: Path) -> None:
        self.buffers.open(path)
        self.center.show_file(path)

    # ------------------------------------------------------- C-x prefix chords
    @property
    def cx_pending(self) -> bool:
        return self._cx_pending

    def action_cx_prefix(self) -> None:
        """Enter pending C-x state; the next key completes the chord."""
        self._set_pending(True)
        # Auto-cancel the prefix if no second key arrives.
        if self._cx_timer is not None:
            self._cx_timer.stop()
        self._cx_timer = self.set_timer(3.0, lambda: self._set_pending(False))

    def _set_pending(self, pending: bool) -> None:
        self._cx_pending = pending
        hint = self.query_one("#prefix-hint", Static)
        hint.set_class(pending, "active")
        if pending:
            hint.update(
                "C-x  (b: buffers  g: git  o: focus  t: workspace  "
                "C-s: save  C-c: quit)"
            )

    def on_key(self, event) -> None:
        """Complete a C-x chord for keys that bubble up (filer / git log focus)."""
        if not self._cx_pending or event.key == "ctrl+x":
            return
        event.stop()
        event.prevent_default()
        self.complete_cx(event.key)

    def complete_cx(self, key: str) -> None:
        """Run the chord for *key* and leave pending state. Called by panes too."""
        self._set_pending(False)
        if self._cx_timer is not None:
            self._cx_timer.stop()
            self._cx_timer = None
        self._run_chord(key)

    def _run_chord(self, key: str) -> None:
        if key == "b":
            self.action_buffer_list()
        elif key == "g":
            self.center.show_git()
        elif key == "o":
            self.action_cycle_focus()
        elif key == "t":
            self.action_spawn_workspace()
        elif key == "ctrl+s":
            self.action_save()
        elif key == "ctrl+c":
            self.action_quit()
        # Unknown second key: prefix simply cancelled (no-op).

    # ------------------------------------------------------------- chord actions
    def action_buffer_list(self) -> None:
        if len(self.buffers) == 0:
            self.notify("No open buffers yet.", severity="warning")
            return

        def _picked(path: Path | None) -> None:
            if path is not None:
                self._open_file(path)

        self.push_screen(BufferList(self.buffers), _picked)

    def action_cycle_focus(self) -> None:
        order = ["filer", "center", "workspace"]
        focused = self.focused
        start = 0
        if focused is not None:
            for i, pane_id in enumerate(order):
                pane = self.query_one(f"#{pane_id}")
                if focused is pane or focused in pane.walk_children():
                    start = (i + 1) % len(order)
                    break
        for offset in range(len(order)):
            pane = self.query_one(f"#{order[(start + offset) % len(order)]}")
            target = pane if pane.focusable else self._first_focusable(pane)
            if target is not None:
                target.focus()
                return

    @staticmethod
    def _first_focusable(widget):
        for child in widget.walk_children():
            if child.focusable:
                return child
        return None

    def action_spawn_workspace(self) -> None:
        """Split a tmux pane to the right running the workspace CLI."""
        ok, message = tmux.spawn_workspace(self.workspace_cmd)
        workspace = self.query_one("#workspace", Workspace)
        if ok:
            workspace.running = True
            self.notify(message)
        else:
            self.notify(message, severity="warning")

    def action_save(self) -> None:
        if not self.center.showing_file:
            self.notify("No file to save.", severity="warning")
            return
        fv = self.center.file_view
        try:
            path = fv.save()
        except RuntimeError as exc:
            self.notify(str(exc), severity="warning")
            return
        self.notify(f"Saved {path.name}")

    def action_toggle_markdown(self) -> None:
        if not self.center.showing_file:
            return
        fv = self.center.file_view
        if not fv.can_toggle_markdown():
            self.notify("Not a Markdown file.", severity="warning")
            return
        rendered = fv.toggle_markdown()
        self.notify("Markdown: rendered" if rendered else "Markdown: raw")
