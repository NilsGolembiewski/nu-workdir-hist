"""Exception types for nu-workdir-hist.

These are caught in the CLI entry point and turned into clear, actionable
stderr messages with non-zero exit codes (rather than tracebacks).
"""

from __future__ import annotations


class NuWorkdirHistError(Exception):
    """Base class for handled CLI errors (exit non-zero, print to stderr)."""


class NoSqliteHistoryError(NuWorkdirHistError):
    """No SQLite history file found (either missing, or plaintext-only backend).

    Carries an actionable message explaining how to enable the sqlite backend
    and migrate with `history import`.
    """


class HistoryError(NuWorkdirHistError):
    """The history DB is unreadable or lacks the expected `history` table."""