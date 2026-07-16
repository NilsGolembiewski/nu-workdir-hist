"""The reedline/nushell `history` SQLite schema, replicated for tests/fixtures.

Source: nushell/reedline `src/history/sqlite_backed.rs`.
The schema is stable across nushell 0.90-0.112+. See
agent_docs/research/2026-07-16-nushell-history-format.md.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Mapping

# PRAGMA application_id used by reedline (constant SQLITE_APPLICATION_ID).
SQLITE_APPLICATION_ID = 1151497937

# reedline requires user_version == 0; non-zero is rejected as an error.
SQLITE_USER_VERSION = 0

# The exact DDL reedline runs when creating the history database.
HISTORY_DDL = """\
create table if not exists history (
    id integer primary key autoincrement,
    command_line text not null,
    start_timestamp integer,
    session_id integer,
    hostname text,
    cwd text,
    duration_ms integer,
    exit_status integer,
    more_info text
) strict;
create index if not exists idx_history_time on history(start_timestamp);
create index if not exists idx_history_cwd on history(cwd);
create index if not exists idx_history_exit_status on history(exit_status);
create index if not exists idx_history_cmd on history(command_line);
create index if not exists idx_history_cmd on history(session_id);
"""

_INSERT_SQL = (
    "INSERT INTO history "
    "(id, command_line, start_timestamp, session_id, hostname, cwd, "
    " duration_ms, exit_status, more_info) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def connect_for_writing(db_path: Path) -> sqlite3.Connection:
    """Open a writable connection and apply reedline's pragmas + DDL.

    Used by tests/fixtures to build a real-schema history DB. Production code
    only ever opens read-only (see `history.py`).
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute(f"PRAGMA application_id = {SQLITE_APPLICATION_ID};")
    conn.execute(f"PRAGMA user_version = {SQLITE_USER_VERSION};")
    conn.executescript(HISTORY_DDL)
    conn.commit()
    return conn


def populate(conn: sqlite3.Connection, rows: Iterable[Mapping]) -> None:
    """Insert rows given as mappings with the meaningful keys.

    Accepted keys: command_line, cwd, start_timestamp, exit_status, id.
    Missing keys default to NULL / 0.
    """
    cur = conn.cursor()
    for r in rows:
        cur.execute(
            _INSERT_SQL,
            (
                r.get("id"),
                r["command_line"],
                r.get("start_timestamp"),
                None,            # session_id
                None,            # hostname
                r.get("cwd"),
                None,            # duration_ms
                r.get("exit_status", 0),
                None,            # more_info
            ),
        )
    conn.commit()