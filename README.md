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
    (scrollable), which **auto-refreshes** so new commits appear on their own
    (the highlighted commit is preserved). Bottom shows the diff for the
    selected commit (unstaged diff by default); the diff is **reloaded on
    demand** with the ⟳ button or `C-r`.
- **Right — Workspace**: a tmux pane running an interactive CLI such as
  `claude code` or GitHub Copilot CLI.

## Status

All four phases implemented (28 tests passing). See
`docs/superpowers/specs/` for the design.

| Phase | Scope | State |
|-------|-------|-------|
| 1 | 3-pane skeleton + filer + file view (syntax highlight) | ✅ |
| 2 | Git view (one-line log + colorized diff, commit selection) | ✅ |
| 3 | Emacs editing (C-x prefix) + buffers (C-x b) + markdown toggle | ✅ |
| 4 | tmux workspace integration | ✅ |

## Keys

| Key | Action |
|-----|--------|
| `C-x b` | switch buffer (recently opened files) |
| `C-x g` | show git view |
| `C-x o` | cycle focus across panes |
| `C-x t` | open the tmux workspace pane |
| `C-r` | reload the git diff (in git view) |
| `C-x C-s` | save the current file |
| `C-x C-c` / `C-q` | quit |
| `F2` | toggle Markdown raw ⇄ rendered |
| `C-a/C-e/C-f/C-b/C-n/C-p` | move (line start/end, char, line) |
| `M-f/M-b`, `M-d` | word move / kill word |
| `C-k` `C-y` | kill line / yank |
| `C-space`, `C-w`, `M-w` | set mark / kill region / copy region |
| `C-s`, `C-_` | search forward / undo |

## Develop

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,syntax]"
.venv/bin/tuuuui            # run
.venv/bin/textual run --dev src/tuuuui/app.py   # dev console
```
