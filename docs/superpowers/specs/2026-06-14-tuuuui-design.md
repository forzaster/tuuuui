# tuuuui — Design

Date: 2026-06-14
Status: Approved (proceeding phased)

## Goal

A Python terminal application: a 3-pane (left / center / right) terminal IDE.

- **Left — Filer**: scrollable file tree. Emacs `C-x b` buffer feature: previously
  opened files appear in a switchable buffer list.
- **Center — Git view / File view**: git view while working; selecting a file in
  the filer switches the center to the file view.
  - *File view*: editable with emacs keybindings (target through `C-x` prefix,
    full-emacs later). Markdown can toggle between raw edit and rendered display.
  - *Git view*: top/bottom split. Top = one-line-per-commit `git log`
    (scrollable). Bottom = unstaged diff by default; selecting a commit shows that
    commit's diff.
- **Right — Workspace**: tmux pane running `claude code` / GitHub Copilot CLI.

## Tech Stack

**Textual 8.x** (chosen). Rationale: rich widgets (`Tree`, `TextArea`,
`ListView`, `DataTable`), CSS-like styling, async-friendly for git subprocess
calls, and `TextArea` ships tree-sitter syntax highlighting + some emacs-ish
keys. Alternatives considered: prompt_toolkit (stronger native emacs editing but
much more UI to hand-build) and urwid/blessed (too low-level). Emacs keybindings
beyond the defaults are custom `Binding`s — equal effort in any library.

The right pane is delegated to **tmux** rather than embedding a PTY inside the
app: most stable way to host interactive CLIs like `claude code`.

## Architecture

Package layout (`src/tuuuui/`):

```
__main__.py        # entry point (`tuuuui` script)
app.py             # TuuuuiApp: 3-pane layout, global bindings, mode switching
core/
  git.py           # async git helpers (log, diff, show) — pure functions
  buffers.py       # BufferManager: ordered list of opened files
widgets/
  filer.py         # Filer(Tree): scrollable file tree, emits FileSelected
  center.py        # Center: container that swaps GitView <-> FileView
  file_view.py     # FileView: TextArea subclass, emacs keys, markdown toggle
  git_view.py      # GitView: top commit log + bottom diff
  workspace.py     # Workspace: right pane; tmux integration / placeholder
  buffer_list.py   # BufferList overlay (C-x b switcher)
```

### Data flow

1. `Filer` emits `FileSelected(path)` → `TuuuuiApp` records it in `BufferManager`
   and tells `Center` to show `FileView` for that path.
2. With no file active (startup / `C-x g`), `Center` shows `GitView`.
3. `GitView` top log emits `CommitSelected(sha)` → bottom diff reloads via
   `core.git.show(sha)` (or `core.git.diff()` for the unstaged default).
4. `C-x b` opens `BufferList` overlay listing `BufferManager` entries; choosing
   one re-shows that file in `Center`.

### Key bindings (global, app level)

- `C-x` is a prefix: app tracks a "pending C-x" state, the next key completes it.
- `C-x b` → buffer switcher. `C-x C-s` → save (Phase 3). `C-x g` → git view.
- `C-x o` → cycle focus across panes. `q`/`C-x C-c` → quit.
- Markdown toggle: `C-c m` (raw <-> rendered).

### Error handling

- Not a git repo / git missing → GitView shows a friendly message, app still runs.
- Binary or unreadable file → FileView shows a notice instead of garbage.
- tmux absent → Workspace shows instructions instead of failing.

### Testing

- `core/git.py` and `core/buffers.py` are pure/IO-thin → unit tested directly.
- Widgets tested with Textual's `App.run_test()` pilot (key presses, messages).

## Phasing

| Phase | Scope | Done when |
|-------|-------|-----------|
| 1 | 3-pane skeleton + Filer + FileView (read-only, syntax highlight) | app runs, tree navigates, file shows |
| 2 | GitView (log top / diff bottom, commit selection) | log scrolls, selecting commit swaps diff |
| 3 | Emacs editing through `C-x` prefix, kill-ring, buffers (`C-x b`), markdown toggle | edit+save works, buffer switch works |
| 4 | tmux workspace integration | launching app lays out tmux with right CLI pane |

Each phase is committed and produces a runnable app.

## Out of scope (YAGNI for now)

- Full emacs (mark/region rectangles, `M-x`) — Phase 3 stops at `C-x` prefix.
- Embedded PTY in-app — delegated to tmux.
- Multi-repo / remote git operations.
