"""An ``OptionList`` that also moves with emacs ``C-n`` / ``C-p``.

Used for every list-style view (the git log and the ``C-x b`` buffer switcher)
so they navigate the same way as the filer — arrows *or* ``C-n`` (down) /
``C-p`` (up). Pure UI: no behaviour beyond the extra key bindings.
"""

from __future__ import annotations

from textual.binding import Binding
from textual.widgets import OptionList


class EmacsOptionList(OptionList):
    """``OptionList`` with emacs ``C-n``/``C-p`` cursor movement."""

    BINDINGS = [
        Binding("ctrl+n", "cursor_down", "Down", show=False),
        Binding("ctrl+p", "cursor_up", "Up", show=False),
    ]
