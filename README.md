# tuuuui

A 3-pane terminal IDE built with [Textual](https://textual.textualize.io/).

```
┌──────────────┬───────────────────────────┬──────────────────┐
│  File tree   │   Git view  /  File view  │   Workspace      │
│  (filer)     │                           │   (tmux: claude  │
│  + buffers   │   editor (emacs keys,     │    code / copilot│
│  (C-x b)     │    markdown toggle)       │    cli)          │
└──────────────┴───────────────────────────┴──────────────────┘
```

## Panes

- **Left — Filer**: scrollable file tree. Emacs `C-x b` opens a buffer list of
  previously opened files for quick switching.
- **Center — Git view / File view**: shows the git view while working; selecting
  a file switches to the file view.
  - *File view*: editable with emacs keybindings; Markdown can toggle between
    raw editing and rendered display via a shortcut key.
  - *Git view*: split top/bottom. Top is one-line-per-commit `git log`
    (scrollable); bottom shows the diff for the selected commit (unstaged diff
    by default).
- **Right — Workspace**: a tmux pane running an interactive CLI such as
  `claude code` or GitHub Copilot CLI.

## Status

Built in phases. See `docs/superpowers/specs/` for the design.

| Phase | Scope |
|-------|-------|
| 1 | 3-pane skeleton + filer + file view (read-only) |
| 2 | Git view (log + diff) |
| 3 | Emacs editing (C-x prefix) + buffers (C-x b) + markdown toggle |
| 4 | tmux workspace integration |

## Develop

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,syntax]"
.venv/bin/tuuuui            # run
.venv/bin/textual run --dev src/tuuuui/app.py   # dev console
```
