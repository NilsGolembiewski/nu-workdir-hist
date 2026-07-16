"""Command-line entry point for `nu-workdir-hist`."""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from . import backend as _backend
from . import history as _history
from . import paths as _paths
from .errors import HistoryError, NoSqliteHistoryError, NuWorkdirHistError

__all__ = ["main", "parse_args", "build_parser"]

DEFAULT_LAST = 50
_LAST_ENV = "NU_WORKDIR_HIST_LAST"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nu-workdir-hist",
        description=(
            "List nushell command-history entries that were executed in the "
            "current working directory (requires the SQLite history backend)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Environment:\n"
            f"  {_paths.NU_HISTORY_PATH_ENV}      path to history.sqlite3 "
            "(same as --history-path)\n"
            f"  {_LAST_ENV}        default for --last (a non-negative integer)\n"
            f"  {_paths.NU_PHYSICAL_ENV}   set to 1 to enable --physical\n\n"
            "Path matching:\n"
            "  By default the current directory is compared to each command's "
            "stored `cwd`\n"
            "  using nushell's logical PWD form (absolute, no trailing slash, "
            "symlink\n"
            "  components preserved). Use --physical to realpath-resolve the "
            "current cwd.\n"
            "  --last 0 means no limit (print all matching commands)."
        ),
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    p.add_argument(
        "-n", "--last",
        type=int, default=None,
        metavar="N",
        help="number of commands to print, most-recent first (default: 50; "
             "0 = no limit / all). Negative values are rejected.",
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="also print the start timestamp and exit status for each command.",
    )
    p.add_argument(
        "--physical",
        action="store_true",
        default=None,
        help="resolve the current working directory with os.path.realpath "
             "(symlink-resolved) before matching, for users whose stored cwd "
             "reflects the physical location.",
    )
    p.add_argument(
        "--history-path",
        default=None,
        metavar="PATH",
        help="path to history.sqlite3 (overrides the nushell config-dir "
             "default; also settable via "
             f"{_paths.NU_HISTORY_PATH_ENV}).",
    )
    return p


def _resolve_last(flag_value: int | None) -> int:
    """Combine the --last flag with the env default, validating the result.

    A negative or non-integer *flag* value is a hard error (exit non-zero).
    A bad *env* value is ignored and falls back to the default — environment
    defaults should never make the tool unusable.
    """
    if flag_value is not None:
        if flag_value < 0:
            print(
                "nu-workdir-hist: error: --last must be a non-negative integer, "
                f"got {flag_value}",
                file=sys.stderr,
            )
            raise SystemExit(2)
        return flag_value

    env = os.environ.get(_LAST_ENV)
    if env is None or env.strip() == "":
        return DEFAULT_LAST
    try:
        value = int(env)
    except ValueError:
        return DEFAULT_LAST
    if value < 0:
        return DEFAULT_LAST
    return value


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse argv, applying env-var defaults and validation.

    Raises SystemExit (non-zero) on invalid input, after printing to stderr —
    matching argparse conventions.
    """
    parser = build_parser()
    ns = parser.parse_args(argv)
    # Re-resolve --last through env + validation so a negative value (which
    # argparse's `type=int` would otherwise accept) is rejected with a clear
    # message, and the env default is applied.
    ns.last = _resolve_last(ns.last)
    # physical: flag (True/False) wins over env.
    if ns.physical is None:
        ns.physical = _paths.physical_from_env(os.environ.get(_paths.NU_PHYSICAL_ENV))
    return ns


# -------------------------------------------------------------- formatting


def _format_line(row: _history.HistoryRow, *, verbose: bool) -> str:
    if not verbose:
        return row.command_line
    ts = row.start_timestamp
    if ts is not None:
        ts_str = _dt.datetime.fromtimestamp(
            ts / 1000.0, tz=_dt.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        ts_str = "-"
    exit_str = row.exit_status if row.exit_status is not None else "-"
    return f"[{ts_str}] exit={exit_str}  {row.command_line}"


# -------------------------------------------------------------- main


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    try:
        ns = parse_args(argv)
    except SystemExit as e:
        # argparse/_resolve_last already printed; surface its code.
        code = e.code if isinstance(e.code, int) else 2
        return code

    try:
        _run(ns)
    except NoSqliteHistoryError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except HistoryError as exc:
        print(f"nu-workdir-hist: error: {exc}", file=sys.stderr)
        return 2
    except NuWorkdirHistError as exc:
        print(f"nu-workdir-hist: error: {exc}", file=sys.stderr)
        return 2
    return 0


def _run(ns: argparse.Namespace) -> None:
    db_path = _paths.resolve_history_path(ns.history_path)
    _backend.detect(db_path)  # raises NoSqliteHistoryError if absent
    cwd = _paths.current_workdir(physical=ns.physical)
    rows = _history.query_history(Path(db_path), cwd, limit=ns.last)
    out = sys.stdout
    for row in rows:
        out.write(_format_line(row, verbose=ns.verbose))
        out.write("\n")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())