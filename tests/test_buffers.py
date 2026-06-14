from pathlib import Path

from tuuuui.core.buffers import BufferManager


def test_open_adds_buffer():
    mgr = BufferManager()
    mgr.open(Path("/tmp/a.py"))
    assert len(mgr) == 1
    assert mgr.current.path == Path("/tmp/a.py")


def test_open_existing_moves_to_front():
    mgr = BufferManager()
    mgr.open(Path("/tmp/a.py"))
    mgr.open(Path("/tmp/b.py"))
    mgr.open(Path("/tmp/a.py"))  # re-open a
    assert len(mgr) == 2
    assert mgr.current.path == Path("/tmp/a.py")
    assert mgr.previous.path == Path("/tmp/b.py")


def test_previous_is_second_mru():
    mgr = BufferManager()
    assert mgr.previous is None
    mgr.open(Path("/tmp/a.py"))
    assert mgr.previous is None  # only one buffer
    mgr.open(Path("/tmp/b.py"))
    assert mgr.previous.path == Path("/tmp/a.py")


def test_close_removes_buffer():
    mgr = BufferManager()
    mgr.open(Path("/tmp/a.py"))
    mgr.open(Path("/tmp/b.py"))
    mgr.close(Path("/tmp/a.py"))
    assert len(mgr) == 1
    assert mgr.current.path == Path("/tmp/b.py")


def test_order_is_mru():
    mgr = BufferManager()
    for p in ["/tmp/a", "/tmp/b", "/tmp/c"]:
        mgr.open(Path(p))
    assert [b.path.name for b in mgr.buffers] == ["c", "b", "a"]
