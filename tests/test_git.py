"""Tests for core.git against a real temporary git repo."""

import asyncio
import subprocess
from pathlib import Path

import pytest

from tuuuui.core import git


def _run(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _run(tmp_path, "init", "-q")
    _run(tmp_path, "config", "user.email", "t@t.local")
    _run(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.txt").write_text("hello\n")
    _run(tmp_path, "add", "a.txt")
    _run(tmp_path, "commit", "-qm", "first commit")
    return tmp_path


def test_is_repo_true(repo: Path):
    assert asyncio.run(git.is_repo(repo)) is True


def test_is_repo_false(tmp_path: Path):
    assert asyncio.run(git.is_repo(tmp_path)) is False


def test_log_returns_commits(repo: Path):
    commits = asyncio.run(git.log(repo))
    assert len(commits) == 1
    assert commits[0].subject == "first commit"
    assert commits[0].author == "t"
    assert len(commits[0].short_sha) >= 7


def test_diff_unstaged(repo: Path):
    (repo / "a.txt").write_text("hello\nworld\n")
    diff = asyncio.run(git.diff_unstaged(repo))
    assert "+world" in diff


def test_show(repo: Path):
    commits = asyncio.run(git.log(repo))
    out = asyncio.run(git.show(repo, commits[0].sha))
    assert "first commit" in out
    assert "a.txt" in out


def test_missing_repo_raises():
    with pytest.raises(git.GitError):
        asyncio.run(git.repo_root(Path("/")))
