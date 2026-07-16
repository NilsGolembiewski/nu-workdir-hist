"""Detect which nushell history backend is in use.

Plaintext (`history.txt`) is nushell's default and stores NO cwd, so cwd
filtering is impossible. We surface a clear, actionable error in that case.
"""

from __future__ import annotations

import enum
from pathlib import Path

from .errors import NoSqliteHistoryError

__all__ = ["Kind", "Detection", "detect", "plaintext_message"]


class Kind(enum.Enum):
    SQLITE = "sqlite"
    # (no other kind is usable by this tool)


class Detection:
    __slots__ = ("kind", "path")

    def __init__(self, kind: Kind, path: Path) -> None:
        self.kind = kind
        self.path = path


def plaintext_message(sqlite_path: Path) -> str:
    """The actionable message shown when only the plaintext backend is found."""
    txt_path = sqlite_path.parent / "history.txt"
    head = (
        f"nu-workdir-hist: no SQLite history file found at {sqlite_path}\n"
        "Nushell's default history backend is plaintext (history.txt), which "
        "does not store\nthe working directory of each command, so filtering "
        "by cwd is impossible."
    )
    if txt_path.exists():
        head += f"\n\nI found a plaintext history at {txt_path}."
    return (
        head
        + "\n\nTo use this tool, enable the SQLite backend and migrate your "
        "existing history:\n\n"
        "    # in config.nu (or $env.config):\n"
        "    $env.config.history.file_format = \"sqlite\"\n\n"
        "    # then migrate your plaintext history into sqlite "
        "(nushell >= 0.100.0):\n"
        "    history import\n"
    )


def detect(sqlite_path: Path) -> Detection:
    """Raise NoSqliteHistoryError if the sqlite file is absent; else return it.

    If a sibling `history.txt` exists we tailor the message to the
    plaintext-backend case; otherwise we still give an actionable no-file error.
    """
    if sqlite_path.exists():
        return Detection(Kind.SQLITE, sqlite_path)
    raise NoSqliteHistoryError(plaintext_message(sqlite_path))