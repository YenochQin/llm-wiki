"""Small helpers for predictable command-line text I/O."""

from __future__ import annotations

import os
import sys
from typing import Any


def _is_utf8(encoding: str | None) -> bool:
    return bool(encoding and encoding.replace("_", "-").lower() in {"utf-8", "utf8"})


def _reconfigure_stream(stream: Any) -> None:
    if stream is None or _is_utf8(getattr(stream, "encoding", None)):
        return
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="replace")


def configure_utf8_stdio() -> None:
    """Use UTF-8 for CLI stdio when the host console defaults otherwise."""
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    _reconfigure_stream(sys.stdin)
    _reconfigure_stream(sys.stdout)
    _reconfigure_stream(sys.stderr)
