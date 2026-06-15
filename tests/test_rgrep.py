"""core.rgrep: ripgrep-backed recursive search (UI-independent)."""

from pathlib import Path

import pytest

from tuuuui.core import rgrep


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "a.py").write_text("alpha\nNEEDLE here\nomega\n")
    (tmp_path / "b.txt").write_text("nothing\nneedle lower\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.py").write_text("deep needle\n")
    return tmp_path


async def test_finds_matches_across_files(tree: Path):
    matches = await rgrep.search(tree, "needle")
    # smart-case: lowercase query matches NEEDLE, needle, etc.
    found = {(m.path.name, m.line) for m in matches}
    assert ("a.py", 2) in found
    assert ("b.txt", 2) in found
    assert ("c.py", 1) in found


async def test_smart_case_is_case_sensitive_for_uppercase(tree: Path):
    matches = await rgrep.search(tree, "NEEDLE")
    found = {(m.path.name, m.line) for m in matches}
    assert ("a.py", 2) in found
    assert ("b.txt", 2) not in found  # lowercase line excluded


async def test_match_carries_text_and_column(tree: Path):
    matches = await rgrep.search(tree, "NEEDLE")
    match = next(m for m in matches if m.path.name == "a.py")
    assert match.text == "NEEDLE here"
    assert match.column == 1
    assert match.path.is_absolute()


async def test_no_matches_returns_empty_list(tree: Path):
    assert await rgrep.search(tree, "zzz-not-present") == []


async def test_empty_pattern_returns_empty_list(tree: Path):
    assert await rgrep.search(tree, "") == []


async def test_max_results_is_capped(tree: Path):
    (tree / "many.txt").write_text("needle\n" * 50)
    matches = await rgrep.search(tree, "needle", max_results=5)
    assert len(matches) == 5


def test_one_line_is_relative_to_root(tmp_path: Path):
    match = rgrep.Match(
        path=(tmp_path / "sub" / "c.py").resolve(),
        line=3,
        column=1,
        text="  deep needle  ",
    )
    assert match.one_line(tmp_path) == "sub/c.py:3: deep needle"
