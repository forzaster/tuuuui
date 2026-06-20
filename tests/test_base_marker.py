"""origin/develop (branch base) marker in the git log view."""

import asyncio
import subprocess
from pathlib import Path

import pytest
from rich.text import Text

from tuuuui.app import TuuuuiApp
from tuuuui.core import git
from tuuuui.widgets.git_view import GitView


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t.local")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.txt").write_text("one\n")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-qm", "base commit")
    return tmp_path


@pytest.fixture
def repo_with_origin(repo: Path) -> Path:
    # Simulate an `origin/develop` remote-tracking branch and origin/HEAD without
    # any network: point them at the (current) base commit, then add work on top.
    _git(repo, "update-ref", "refs/remotes/origin/develop", "HEAD")
    _git(repo, "symbolic-ref", "refs/remotes/origin/HEAD",
         "refs/remotes/origin/develop")
    (repo / "a.txt").write_text("two\n")
    _git(repo, "commit", "-aqm", "feature work")
    return repo


# ------------------------------------------------------------- core: git.rev
def test_rev_resolves_head(repo: Path):
    sha = asyncio.run(git.rev(repo, "HEAD"))
    assert sha is not None and len(sha) == 40


def test_rev_returns_none_for_unknown_ref(repo: Path):
    assert asyncio.run(git.rev(repo, "origin/nope")) is None


# ------------------------------------------------------- core: git.base_ref
def test_base_ref_reads_origin_head(repo_with_origin: Path):
    assert asyncio.run(git.base_ref(repo_with_origin)) == "origin/develop"


def test_base_ref_none_without_remote(repo: Path):
    assert asyncio.run(git.base_ref(repo)) is None


# ------------------------------------------------------- widget: the marker
async def _settle(pilot, n: int = 6):
    for _ in range(n):
        await pilot.pause()


async def test_base_commit_row_is_marked_and_colored(repo_with_origin: Path):
    base_sha = await git.rev(repo_with_origin, "origin/develop")
    app = TuuuuiApp(repo_with_origin)
    async with app.run_test() as pilot:
        await _settle(pilot)
        log = app.query_one(GitView).query_one("#log")
        option = log.get_option(base_sha)
        prompt = option.prompt
        assert isinstance(prompt, Text)
        assert "origin/develop" in prompt.plain
        # A distinct colour is applied to the marker (not the default style).
        assert any("magenta" in str(span.style) for span in prompt.spans)


async def test_non_base_commit_row_has_no_marker(repo_with_origin: Path):
    head_sha = await git.rev(repo_with_origin, "HEAD")
    app = TuuuuiApp(repo_with_origin)
    async with app.run_test() as pilot:
        await _settle(pilot)
        log = app.query_one(GitView).query_one("#log")
        prompt = log.get_option(head_sha).prompt
        text = prompt.plain if isinstance(prompt, Text) else str(prompt)
        assert "origin/develop" not in text
