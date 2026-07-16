# nu-workdir-hist Development Report

**Date:** 2026-07-16
**Status:** complete

> 2026-07-16 remediation: wired `--version` (`action="version"`) to
> `build_parser` using `__version__` from `nu_workdir_hist/__init__.py` so
> `nu-workdir-hist --version` prints `nu-workdir-hist 0.1.0` and exits 0;
> > added focused CLI tests for it.
>
> 2026-07-16 ordering reversal: the tool now lists matching commands
> oldest-first (chronological) instead of most-recent-first. `--last N`
> (default 50) still selects the N most-recent matching rows (by `id DESC`),
> which are then printed oldest-first (reversed for display). `--last 0`
> still means "all", oldest-first. Tests and README updated.

## What Changed

Built a pipx-installable Python CLI package `nu-workdir-hist` from scratch under
`/workspace`. New files:

- `pyproject.toml` — project metadata, `nu-workdir-hist = "nu_workdir_hist.cli:main"`
  console-script entry point, `uv_build` build backend (src layout), pytest config,
  dev dependency group (`pytest`).
- `LICENSE` — MIT.
- `README.md` — install (`pipx`/`uv tool`), usage, flags table, history-file
  location per OS, path-canonicalization notes, the sqlite requirement, and the
  plaintext-backend error explanation.
- `src/nu_workdir_hist/__init__.py` — package init + `__version__`.
- `src/nu_workdir_hist/__main__.py` — `python -m nu_workdir_hist` support.
- `src/nu_workdir_hist/schema.py` — the reedline `history` table DDL, pragmas,
  and helpers (`connect_for_writing`, `populate`) used by tests/fixtures to build
  a real-schema DB.
- `src/nu_workdir_hist/errors.py` — `NuWorkdirHistError` hierarchy
  (`NoSqliteHistoryError`, `HistoryError`) so the CLI prints clean messages
  instead of tracebacks.
- `src/nu_workdir_hist/paths.py` — nushell config-dir / `history.sqlite3`
  resolution (`XDG_CONFIG_HOME` honored on all OSes, then per-OS defaults), the
  `--history-path`/`NU_HISTORY_PATH` override ladder, and cwd canonicalization
  (logical vs physical).
- `src/nu_workdir_hist/history.py` — read-only (`?mode=ro`) SQLite query:
  `WHERE cwd IS NOT NULL AND cwd = ? ORDER BY id DESC LIMIT ?`, returning
  `HistoryRow` dataclasses.
- `src/nu_workdir_hist/backend.py` — backend detection; actionable
  plaintext/missing-file error message.
- `src/nu_workdir_hist/cli.py` — argparse CLI, env-var defaults, output
  formatting (plain + `--verbose`), entry point `main()`.
- `tests/conftest.py` — fixtures: real-schema temp DB, `populated_db` with two
  real cwd dirs + a NULL-cwd row, `proj_dir`/`other_dir`, `chdir_to`,
  `isolated_cwd`.
- `tests/test_paths.py`, `tests/test_canonicalization.py`,
  `tests/test_history_query.py`, `tests/test_backend.py`, `tests/test_cli.py`
  — 59 tests covering path resolution, canonicalization, the query/filter logic,
  backend detection messaging, CLI arg parsing + env handling, and end-to-end
  behavior (including a subprocess integration test).

## Why

The user wanted a pipx-installable CLI that lists nushell command-history entries
executed in the current working directory, using `uv` as the package manager,
with canonicalized paths and a configurable "last N" (default 50). Nushell's
default plaintext backend stores no cwd, so the tool must require the sqlite
backend and guide users toward it.

## Approach

- **Package manager / build backend:** `uv` with the `uv_build` backend
  (`requires = ["uv_build>=0.11.28,<0.12"]`, src layout via
  `[tool.uv.build-backend] module-root = "src"`). Confirmed against uv's current
  build-backend docs via Context7.
- **Schema fidelity:** `schema.py` contains the exact reedline DDL (STRICT
  `history` table, `application_id`/`user_version = 0` pragmas, indexes) so test
  fixtures are byte-compatible with real nushell history DBs. Column names used
  by the tool: `command_line` (command text), `cwd` (working dir), `id` (recency
  ordering), `start_timestamp`, `exit_status`.
- **Read-only access:** the DB is opened with a `file:…?mode=ro` URI so the tool
  never locks a running nushell (WAL allows concurrent readers). A test asserts
  writes through such a connection fail.
- **Path canonicalization:** nushell stores each command's `cwd` as its logical
  `$env.PWD` — absolute, no trailing slash, possibly containing symlink
  components (NOT realpath-resolved). The tool matches that form by default:
  `current_workdir(physical=False)` prefers nushell's logical PWD from the `$PWD`
  env var (which nushell maintains) when set and absolute, because
  `os.getcwd()`/`Path.cwd()` return the *physical* path on Linux and would
  mismatch a logical stored cwd. Both sides are normalized to absolute +
  trailing-separator-stripped (root preserved). `--physical`
  (or `NU_WORKDIR_HIST_PHYSICAL=1`) switches the current-cwd side to
  `os.path.realpath` for users whose stored cwd reflects the physical location.
- **Limit semantics:** `--last N` / `-n N` (default 50). `0` = no limit (SQLite
  `LIMIT -1`). Negative *flag* values exit non-zero with a clear stderr message;
  a bad (non-integer or negative) `NU_WORKDIR_HIST_LAST` env value is ignored and
  falls back to the default so a misconfigured env never breaks the tool. Flag
  overrides env.
- **History path ladder:** `--history-path` flag > `NU_HISTORY_PATH` env >
  per-OS config-dir default (`$XDG_CONFIG_HOME/nushell`, else Linux
  `~/.config/nushell`, macOS `~/Library/Application Support/nushell`, Windows
  `%APPDATA%\nushell`) + `history.sqlite3`. Empty strings are treated as unset.
- **Plaintext/missing backend:** if `history.sqlite3` is absent, the tool prints
  an actionable stderr message (mentions `file_format = "sqlite"` and
  `history import`, and notes a sibling `history.txt` if present) and exits 2.
- **Output:** one command per line, oldest-first (chronological order). The N
  most-recent matching rows are selected (by `id DESC LIMIT N`) and then
  reversed for display so the output reads oldest→newest. `--verbose` prefixes
  each line with `[<ISO-UTC timestamp>] exit=<code>  `.

## Tests

59 tests, all green (`uv run pytest`). Coverage:

- **`test_paths.py` (8):** XDG_CONFIG_HOME honored on all platforms; Linux/macOS
  defaults; XDG wins over macOS default; flag > env > default ladder; empty flag
  treated as unset.
- **`test_canonicalization.py` (10):** trailing-slash stripping; root preserved;
  relative→absolute; arbitrary absolute symlink path kept verbatim (logical);
  `current_workdir` honors `$PWD` in logical mode and resolves realpath in
  physical mode; falls back to `Path.cwd()` when `$PWD` unset; env truthiness
  parsing.
- **`test_history_query.py` (10):** most-recent-first ordering; NULL cwd and
  other-cwd rows excluded; `LIMIT` caps; `LIMIT 0` = all; unknown cwd → empty;
  metadata carried on `HistoryRow`; read-only connection verified; missing
  `history` table → `HistoryError`; corrupt/non-sqlite file → `HistoryError`.
- **`test_backend.py` (3):** sqlite present → detected; plaintext-only →
  `NoSqliteHistoryError` with the actionable message; missing entirely →
  `NoSqliteHistoryError`.
- **`test_cli.py` (28):** arg parsing defaults/flags/`--last 0`; verbose/physical
  flags; `--history-path`; negative `--last` rejected with stderr; env defaults
  for `--last` and `--physical` (flag overrides env, bad env falls back); main()
  end-to-end against the temp DB (most-recent-first, limit caps, `0`=all, no
  matches print nothing, verbose ISO timestamp + exit, plaintext/missing errors
  non-zero, env `NU_HISTORY_PATH`, flag overrides env, `--physical` symlink
  resolution); `--help` subprocess; subprocess integration test running the
  installed interpreter module against a fresh temp DB.

Run: `uv run pytest` (61 tests; `--version` support added in 2026-07-16 remediation).

## Verification

**Tests:**
```
$ uv run pytest
============================= test session info ==============================
collected 59 items
tests/test_backend.py ........... [ 5%]
tests/test_canonicalization.py .......... [ 22%]
tests/test_cli.py ............................ [ 69%]
tests/test_history_query.py .......... [ 86%]
tests/test_paths.py ........ [100%]
============================== 59 passed in 0.41s ==============================
```

**Build:**
```
$ uv build
Building source distribution (uv build backend)...
Building wheel from source distribution (uv build backend)...
Successfully built dist/nu_workdir_hist-0.1.0.tar.gz
Successfully built nu_workdir_hist-0.1.0-py3-none-any.whl
```
The wheel contains the package, LICENSE, and the `nu-workdir-hist` entry point.

**pipx install + on-PATH command:**
```
$ pipx install --force .
  installed package nu-workdir-hist 0.1.0
  These apps are now globally available
    - nu-workdir-hist
$ which nu-workdir-hist
/home/hostuser/.local/bin/nu-workdir-hist
$ nu-workdir-hist --help
usage: nu-workdir-hist [-h] [-n N] [-v] [--physical] [--history-path PATH]
List nushell command-history entries that were executed in the current
working directory (requires the SQLite history backend). ...
```

**Manual end-to-end against a real-schema temp DB** (using the pipx-installed
binary, run from a directory whose path matches a stored `cwd`):
```
$ nu-workdir-hist --history-path /tmp/.../history.sqlite3 -n 10   # from proj/
cargo test
cargo build
ls
$ nu-workdir-hist --history-path /tmp/.../history.sqlite3 -v -n 2
[2023-11-14T22:13:29Z] exit=1  cargo test
[2023-11-14T22:13:25Z] exit=0  cargo build
```

**Physical-vs-logical symlink verification:**
- Stored `cwd` = real path `/tmp/.../proj`; run from a symlink `…/link → proj`
  with `$PWD=…/link`.
  - `--physical`: matches (rc 0, prints `pwd`) — realpath resolves the symlink
    back to the stored real path.
  - logical (default): does not match (rc 0, empty output) — the logical PWD
    (`…/link`) differs from the stored real `cwd`, exactly as expected.

**Plaintext backend error (exit 2):**
```
$ nu-workdir-hist --history-path /tmp/.../nushell/history.sqlite3   # only history.txt present
nu-workdir-hist: no SQLite history file found at /tmp/.../nushell/history.sqlite3
Nushell's default history backend is plaintext (history.txt), which does not store
the working directory of each command, so filtering by cwd is impossible.

I found a plaintext history at /tmp/.../nushell/history.txt.

To use this tool, enable the SQLite backend and migrate your existing history:
    $env.config.history.file_format = "sqlite"
    history import
```

**Missing `history` table (exit 2):**
```
nu-workdir-hist: error: history DB at /tmp/.../bad.sqlite3 is unreadable or
missing the `history` table: ...
```

## Caveats

- **Logical-PWD reliance:** logical mode (default) matches the stored `cwd`
  against nushell's logical PWD taken from the `$PWD` env var. This is the most
  faithful comparison when the tool is run from the same logical path nushell was
  in. If a launcher strips `$PWD`, the tool falls back to `Path.cwd()` (physical),
  which may mismatch symlinked stored cwds — use `--physical` in that case. This
  is documented in `--help` and the README.
- **No `config.nu` parsing:** a custom `$env.config.history.path` (nushell
  0.112.1+) is not read from the user's config; users must pass
  `--history-path` or set `NU_HISTORY_PATH`. Documented.
- **Stored cwd normalization is exact-match only:** the tool does `cwd = ?`
  exact comparison (no prefix/subdir matching). A `--prefix` mode was explicitly
  out of scope. Both sides are normalized to absolute + no trailing slash, so a
  trailing-slash difference is tolerated, but any other string difference (case
  on case-sensitive filesystems, symlink vs real) is not — `--physical` covers
  the symlink case.
- **Plaintext is nushell's default backend**, so out-of-the-box many users will
  hit the actionable error until they switch to sqlite and run `history import`.
  This is by design (plaintext stores no cwd) and clearly communicated.
- **No shell completions / no write support** (out of scope).