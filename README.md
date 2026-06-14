# tuuuui

**tuuuui** is a lightweight terminal IDE. A file tree on the left, a git view /
emacs editor in the center, and a workspace for an AI CLI on the right; the
editor is driven by emacs keybindings. Built with the Python TUI framework
[Textual](https://textual.textualize.io/).

The app itself focuses on **2 panes** (filer + center); the right-hand workspace
is launched as a **real tmux split pane** beside it rather than an in-app widget.

```
┌──────────────┬───────────────────────────┐ ┆ tmux split pane
│  Filer       │  Git view  /  File view   │ ┆ ┌──────────────┐
│  (file tree) │                           │ ┆ │ claude code /│
│  + buffers   │  emacs editor /           │ ┆ │ copilot cli  │
│  (C-x b)     │  git log + diff           │ ┆ │  (C-x t)     │
└──────────────┴───────────────────────────┘ ┆ └──────────────┘
        tuuuui app (2 panes)                      tmux pane
```

| Git view | File view | Markdown |
|----------|-----------|----------|
| ![git view](docs/images/gitview.svg) | ![file view](docs/images/fileview.svg) | ![markdown](docs/images/markdown.svg) |

---

## Overview

A tool for editing source, reviewing git history, and talking to an AI CLI on a
single screen without leaving the terminal. Each of the panes has a distinct
role.

- **Left — Filer**: a scrollable file tree. Opened files are remembered as
  buffers and can be listed/switched with emacs `C-x b`.
- **Center — Git view / File view**: shows the git view while you work; selecting
  a file in the filer switches it to the file view.
- **Right — Workspace (tmux)**: interactive CLIs such as `claude code` or GitHub
  Copilot CLI run in a **tmux split pane** beside the app rather than as an
  embedded PTY or an in-app pane (most stable). The app itself stays focused on
  the two left panes.

---

## Features

### Filer (left)
- Scrollable directory tree.
- **Emacs navigation**: in addition to the arrow keys, `C-n`/`C-p` (down/up),
  `C-f`/`C-b` (next/parent), `C-v`/`M-v` (page) move through the tree.
- **Changed-file highlighting**: files included in the diff currently shown in
  the git view (selected commit or unstaged) are highlighted with a yellow `*`.
- **Filter**: turning on the "Changed only" checkbox at the top narrows the tree
  to just the diff's files (only directories that contain a changed file remain).
- **Buffers**: opened files are kept in most-recently-used order and switched
  from a popup with `C-x b`; the previous buffer is preselected (like emacs).

![filer changed files](docs/images/filer.svg)

### File view (center)
- **Syntax highlighting**: tree-sitter based coloring of keywords, strings, and
  comments for Python / Markdown / JSON / TOML / YAML / JS / TS / Go / Rust and
  other major languages.
- **Emacs editing**: cursor movement, deletion, a **kill-ring** (kill/yank),
  **mark/region**, undo, forward search, and save (`C-x C-s`).
- **Markdown toggle**: Markdown files switch between raw editing and a rendered
  view with `F2`.

### Git view (center)
- Split top/bottom.
- **Top**: a selectable list whose first two rows are the working-tree
  **● Unstaged changes** / **● Staged changes**, followed by `git log` one line
  per commit (scrollable). The commit part **auto-refreshes** so new commits
  appear on their own (the highlighted row and scroll position are preserved).
- **Bottom**: the diff for the highlighted row — unstaged diff / staged diff
  (`git diff --cached`) / the selected commit's diff. The diff does not auto-poll;
  reload it explicitly with the ⟳ button or `C-r` (handy while editing). Added =
  green, removed = red, hunk = cyan.
- The files in the shown diff also drive the filer's markers and the "Changed
  only" filter (works for Unstaged, Staged, and any commit).

### Workspace (right)
- Inside tmux, `C-x t` (or `--tmux` at launch) splits a CLI pane on the right.
- The command is set with `--workspace CMD` or the `TUUUUI_WORKSPACE_CMD`
  environment variable (default: `claude`).
- The pane reflects whether tmux is present and running.

---

## Tech stack

| Area | Choice | Why |
|------|--------|-----|
| Language | Python (>=3.10) | — |
| TUI | **Textual 8.x** | High-level widgets (`Tree` / `TextArea` / `OptionList`), CSS-like styling, and async (await git in a subprocess) get to a working app fastest. `TextArea` ships tree-sitter highlighting. |
| Editor base | subclass of `textual.widgets.TextArea` | Emacs keys (`C-x` prefix, kill-ring, etc.) added via `Binding` and custom handling. |
| Workspace | delegated to **tmux** | A tmux split pane is more stable than embedding an interactive CLI as a PTY. |
| Git | shell out to the `git` CLI | Implemented as UI-independent pure functions (`core/git.py`), easy to test. |
| Tests | `pytest` + Textual's `App.run_test()` pilot | Core is unit tested; widgets are verified by simulating key presses. |

> Alternatives considered: `prompt_toolkit` (natively strong emacs editing but
> much more UI to hand-build) and `urwid`/`blessed` (lightweight but weak modern
> async/widgets). Because this app is UI-heavy (tree, diff, log, Markdown
> rendering), Textual was chosen.

### Layout

```
src/tuuuui/
  __main__.py          entry point (the `tuuuui` command)
  launcher.py          tuuuui-tmux: one-shot launcher (tmux + 2-pane layout)
  app.py               TuuuuiApp: 2-pane layout, C-x prefix, mode switching
  app.tcss             layout styles
  core/
    git.py             async git helpers (log / diff / show)
    buffers.py         BufferManager: MRU buffer management
    tmux.py            launching the tmux split pane
  widgets/
    filer.py           left: file tree (emacs navigation)
    center.py          center: GitView <-> FileView switching
    file_view.py       center: editor + Markdown rendering
    git_view.py        center: commit log + diff
    emacs.py           emacs keybinding layer (EmacsTextArea)
    search.py          C-s search modal
    buffer_list.py     C-x b buffer-switch modal
docs/superpowers/specs/ design document
tests/                  test suite
```

---

## Install

```bash
git clone git@github.com:forzaster/tuuuui.git
cd tuuuui
python3 -m venv .venv
.venv/bin/pip install -e .          # includes the syntax-highlighting deps
```

## Usage

```bash
# Open the current directory
.venv/bin/tuuuui

# Open a specific directory
.venv/bin/tuuuui ~/path/to/project

# Inside tmux: launch and auto-split a claude code pane on the right
.venv/bin/tuuuui --tmux

# Change the CLI launched in the workspace
.venv/bin/tuuuui --tmux --workspace "copilot"
```

### Launch tmux + tuuuui + workspace in one command

The dedicated launcher `tuuuui-tmux` creates a tmux session, runs tuuuui on the
left and the AI CLI on the right, focuses tuuuui, and attaches — all in one go.

**Prerequisites**

- **tmux** installed (`brew install tmux` / `apt install tmux`, etc.).
- The **AI CLI** for the right pane on your `PATH` (e.g. `claude`, or the GitHub
  Copilot CLI `copilot`).
- **tuuuui** installed (see Install above; `tuuuui-tmux` is installed with it).
  When using a venv, put `.venv/bin/` on your `PATH` or call
  `.venv/bin/tuuuui-tmux` directly.

**Usage**

```bash
# Current directory. Left = tuuuui, right = claude (default)
tuuuui-tmux

# Specify a directory + use copilot in the right pane
tuuuui-tmux ~/path/to/project --workspace copilot

# 40% width for the workspace pane, session name "dev"
tuuuui-tmux --percent 40 --session dev
```

- The default right-pane command can also be set via the `TUUUUI_WORKSPACE_CMD`
  environment variable.
- If run from inside tmux, it splits the current window instead of nesting a new
  session (delegates to `tuuuui --tmux`).

**Plain tmux one-liner** (no extra tooling; assumes `tuuuui` and `claude` are on
your `PATH`):

```bash
tmux new-session 'tuuuui' \; split-window -h -d -l 30% 'claude'
```

Basic flow: pick a file in the left tree to switch the center to the file view,
edit with emacs keys, save with `C-x C-s`. Return to the git view with `C-x g`,
select a commit to inspect its diff, refresh with `C-r`. Jump to a previously
opened file with `C-x b`. Start the AI CLI on the right with `C-x t`.

### Keybindings

| Key | Action |
|-----|--------|
| `C-x b` | switch buffer (recently opened files) |
| `C-x g` | show the git view |
| `C-x o` | cycle focus between panes |
| `C-x t` | launch the tmux workspace pane |
| `C-x C-s` | save the file |
| `C-x C-c` | close the file and return to the git view |
| `C-q` | quit the app |
| `F2` | Markdown raw ⇄ rendered |
| `C-r` | reload the git diff (in the git view) |
| `C-a` / `C-e` | line start / end |
| `C-f` / `C-b` / `C-n` / `C-p` | move by character / line |
| `M-f` / `M-b` / `M-d` | word move / kill word |
| `C-d` / `C-h` | delete next / previous character |
| `C-k` / `C-y` | kill line / yank (paste) |
| `C-space` / `C-w` / `M-w` | set mark / kill region / copy region |
| `C-s` | search forward |
| `C-/` / `C-_` / `C-z` | undo |

> `C-x` is a prefix key. Pressing `C-x` shows a hint at the bottom; pressing the
> second key then runs the command. The second key is intercepted even while
> editing, so the prefix takes precedence over text input in the editor.

---

## Development

```bash
.venv/bin/pip install -e ".[dev]"

# tests
.venv/bin/python -m pytest -q

# Textual dev console (run `textual console` in another terminal)
.venv/bin/textual run --dev src/tuuuui/app.py
```

See [`docs/superpowers/specs/2026-06-14-tuuuui-design.md`](docs/superpowers/specs/2026-06-14-tuuuui-design.md)
for the design.

## Status

All four phases implemented (51 tests passing).

| Phase | Scope | State |
|-------|-------|-------|
| 1 | 2-pane skeleton + filer + file view (syntax highlight) | ✅ |
| 2 | Git view (one-line log + colorized diff, commit selection, log auto-refresh / manual diff reload, Unstaged/Staged rows) | ✅ |
| 3 | Emacs editing (`C-x` prefix) + buffers (`C-x b`) + Markdown toggle | ✅ |
| 4 | tmux workspace integration + `tuuuui-tmux` launcher | ✅ |

## License

[MIT](LICENSE)
