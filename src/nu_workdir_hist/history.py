"""Read nushell's SQLite history, filtered by cwd, most-recent first.

The DB is opened read-only (`?mode=ro`) to avoid locking a running nushell
(which opens it with WAL journaling). See the research report for the schema.
"""

from __future__ import annotations

import dataclasses
import sqlite3
from pathlib import Path
from urllib.parse import quote

from .errors import HistoryError

__all__ = ["HistoryRow", "query_history"]

_SELECT_SQL = (
    "SELECT command_line, cwd, start_timestamp, exit_status, id "
    "FROM history "
    "WHERE cwd IS NOT NULL AND cwd = ? "
    "ORDER BY id DESC "
    "LIMIT ?"
)
# LIMIT of -1 means "no limit" in SQLite.
_NO_LIMIT = -1


@dataclasses.dataclass(frozen=True)
class HistoryRow:
    """A single history entry relevant to the tool."""

    command_line: str
    cwd: str
    start_timestamp: int | None
    exit_status: int | None
    id: int


def _ro_uri(db_path: Path) -> str:
    # file: URI with read-only mode; quote the path in case of odd chars.
    p = str(db_path.resolve())
    return "file:" + quote(p) + "?mode=ro"


def query_history(db_path: Path, cwd: str, *, limit: int) -> list[HistoryRow]:
    """Return history rows for `cwd`, most-recent first, capped at `limit`.

    `limit == 0` means no limit (return all matching rows). NULL cwds are
    excluded. Raises :class:`HistoryError` if the DB is unreadable or lacks
    the expected `history` table.
    """
    effective_limit = _NO_LIMIT if limit <= 0 else limit
    try:
        con = sqlite3.connect(_ro_uri(db_path), uri=True)
    except sqlite3.Error as exc:
        raise HistoryError(f"cannot open history DB {db_path}: {exc}") from exc

    try:
        con.row_factory = sqlite3.Row
        cur = con.execute(_SELECT_SQL, (cwd, effective_limit))
        rows: list[HistoryRow] = [
            HistoryRow(
                command_line=r["command_line"],
                cwd=r["cwd"],
                start_timestamp=r["start_timestamp"],
                exit_status=r["exit_status"],
                id=r["id"],
            )
            for r in cur
        ]
        return rows
    except sqlite3.Error as exc:
        raise HistoryError(
            f"history DB at {db_path} is unreadable or missing the `history` "
            f"table: {exc}"
        ) from exc
    finally:
        con.close()