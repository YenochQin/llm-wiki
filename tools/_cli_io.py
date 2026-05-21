"""Small helpers for predictable command-line text I/O."""

from __future__ import annotations

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
    """Use UTF-8 for CLI stdout/stderr when the host console defaults otherwise."""
    _reconfigure_stream(sys.stdout)
    _reconfigure_stream(sys.stderr)
