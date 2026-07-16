# Verification: nu-workdir-hist CLI package

**Date:** 2026-07-16
**Scope:** Independent end-to-end verification of the `nu-workdir-hist` pipx-installable
Python CLI package (src layout at `/workspace`). Acceptance criteria 1–6 from the
verification handoff, checked by actually running the test suite, building, installing
via pipx and `uv tool`, and exercising the installed CLI against a fresh temp sqlite
history DB I created myself with the real reedline schema (independent of the
implementer's fixtures).
**Verdict:** PASS-WITH-ISSUES

## Outcome

partial

## Summary

The package is substantially complete and correct. The test suite (59 tests) is green
and the tests are meaningful — they exercise real query/filter/canonicalization logic
(most-recent-first ordering, NULL/other-cwd exclusion, limit caps, symlink resolution,
read-only connection verification, corrupt-DB handling, the flag/env override ladder),
not stubs. `uv build` produces a wheel and sdist; both `pipx install` and
`uv tool install` produce a working `nu-workdir-hist` command that responds to `--help`.
End-to-end checks against a temp DB built with the *real* reedline DDL
(`PRAGMA application_id=1151497937`, `user_version=0`, STRICT `history` table) confirm
cwd filtering, most-recent-first ordering, the default-50 / `--last N` / `-n 0`=all /
negative-rejected semantics, NULL-cwd and other-cwd exclusion, and the
`--physical` symlink-resolution behavior. Plaintext-only and missing-DB cases print
actionable messages and exit non-zero. The README documents install (pipx/uv tool),
usage, all flags, per-OS history paths, canonicalization, and the sqlite requirement.

**One defect** was found: the CLI does not implement a `--version` (or `-V`) flag, which
criterion #2 explicitly requires ("responds to `--help` and `--version`"). `--help`
works; `--version` exits rc 2 with "unrecognized arguments". The package does define
`__version__ = "0.1.0"` in `src/nu_workdir_hist/__init__.py` — it just isn't wired into
argparse (e.g. via `action="version"`). This is a minor, trivially-fixable gap; all
other criteria pass.

## Verdict

PASS-WITH-ISSUES

## Criteria results

### 1. `uv run pytest` is green and tests are meaningful — PASS

Ran `uv run pytest -v` from `/workspace`. Result: **59 passed in 0.43s** (Python 3.14.6,
pytest 9.1.1).

I read every test file (`tests/test_backend.py`, `test_canonicalization.py`,
`test_cli.py`, `test_history_query.py`, `test_paths.py`) and `conftest.py`. The tests
genuinely exercise behavior, not stubs:

- `test_history_query.py` asserts most-recent-first ordering (`["rm -rf build", "git status", "ls -la"]`),
  NULL-cwd exclusion (`"imported-no-cwd" not in …`), other-cwd exclusion, limit caps, `limit=0`=all,
  unknown-cwd→empty, metadata carried on `HistoryRow`, that a `?mode=ro` connection
  rejects writes, and that a corrupt file / missing `history` table raises `HistoryError`.
- `test_canonicalization.py` asserts trailing-slash stripping, root preservation,
  relative→absolute, symlink-component preservation (logical), `$PWD`-honoring in logical
  mode, `realpath` resolution in physical mode, and env-truthiness parsing.
- `test_cli.py` covers arg parsing, env-vs-flag precedence, negative `--last` rejection,
  end-to-end `main()` output ordering/limits/verbose/plaintext-error, and a real
  subprocess integration test running `python -m nu_workdir_hist` against a fresh DB.
- `test_paths.py` covers XDG/OS-default resolution and the flag>env>default ladder.
- `test_backend.py` covers sqlite-present, plaintext-only (asserts message contains
  `file_format`, `history import`, the sqlite path), and missing-entirely cases.

Fixtures use `connect_for_writing`/`populate` which apply the *exact* reedline DDL and
pragmas, so tests run against a schema byte-compatible with real nushell history.

### 2. `uv build` produces a wheel; `pipx install .` / `uv tool install .` install a working command responding to `--help` and `--version` — PARTIAL FAIL

- `uv build` produced `dist/nu_workdir_hist-0.1.0-py3-none-any.whl` and
  `dist/nu_workdir_hist-0.1.0.tar.gz` (verified `ls dist/`).
- `pipx install --force dist/nu_workdir_hist-0.1.0-py3-none-any.whl` →
  `installed package nu-workdir-hist 0.1.0`; `which nu-workdir-hist` →
  `/home/hostuser/.local/bin/nu-workdir-hist`.
- `nu-workdir-hist --help` → rc 0, full usage printed. ✅
- `uv tool install --force /workspace/dist/nu_workdir_hist-0.1.0-py3-none-any.whl` →
  `Installed 1 executable: nu-workdir-hist`; the binary runs against a temp DB (rc 0).
  ✅
- **`nu-workdir-hist --version` → rc 2, `error: unrecognized arguments: --version`.** ❌
  (Also tried `-V`: rc 2, same "unrecognized arguments".) The package defines
  `__version__ = "0.1.0"` in `src/nu_workdir_hist/__init__.py` but the argparse parser in
  `cli.py` never wires it (no `action="version"` argument). The implementer's own
  development report's "Verification" section only demonstrates `--help` and omits
  `--version`, so this requirement slipped.

Because `--help` works but `--version` does not, this criterion is a **partial fail**.
It is the single blocking-ish item; the fix is a one-line
`p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")`.

### 3. End-to-end against a temp `history.sqlite3` with the REAL reedline schema — PASS

I built my own temp DB independently (not via the package's fixtures) using the exact
DDL from the research report:

```
PRAGMA application_id = 1151497937;   -- confirmed: 1151497937
PRAGMA user_version = 0;              -- confirmed: 0
CREATE TABLE history (...) strict;     -- with all 5 indexes
```

Inserted 59 rows: 55 with `cwd = <proj dir>`, 3 with `cwd = <other dir>`, 1 with
`cwd = NULL`. Ran the pipx-installed `nu-workdir-hist --history-path <db>` from the
proj dir with `PWD=<proj>`:

| Sub-check | Command | Observed | Pass |
| --- | --- | --- | --- |
| Only matching-cwd, most-recent first | `--last 5` | `proj-cmd-55,54,53,52,51` (ids desc) | ✅ |
| Default prints last 50 | (no `-n`) | exactly **50** lines, `proj-cmd-55`→`proj-cmd-06` | ✅ |
| `--last N` controls count | `--last 5` / `--last 3` | 5 / 3 lines | ✅ |
| `-n N` short form | `-n 3` | 3 lines | ✅ |
| `0` prints all | `-n 0` | **55** lines (all matching) | ✅ |
| Negative N errors non-zero | `-n -5` | rc **2**, stderr: `--last must be a non-negative integer, got -5` | ✅ |
| NULL-cwd excluded | `-n 0` | `null-cmd-no-cwd` absent (grep count 0) | ✅ |
| Other-cwd excluded | run from `other/` | only `other-cmd-58,57,56` | ✅ |
| Unknown cwd → empty | run from a dir with no rows | rc 0, empty output | ✅ |
| Verbose format | `-v -n 2` | `[2023-11-14T22:14:15Z] exit=0  proj-cmd-55` etc. | ✅ |

The DB my temp schema used (`application_id`/`user_version`/STRICT table/5 indexes) is
the real reedline schema per the research report; the tool read it without issue,
confirming schema compatibility on the read path.

### 4. Canonicalization: logical vs physical, symlinks, trailing slashes — PASS

- **`--physical` resolves symlinks:** created `link-to-proj → proj`; stored cwd = real
  `proj` path; ran from `link-to-proj` with `PWD=<link>`.
  - Logical (default): empty output (logical PWD=`link` ≠ stored real cwd) — rc 0. ✅
  - `--physical`: `proj-cmd-55,54,53` (realpath resolves symlink → matches stored real
    cwd) — rc 0. ✅ This is exactly the behavior the criterion specifies.
- **Current-side trailing slash tolerated:** nushell stores cwd without trailing
  slashes (research report §3). Ran with `PWD=<proj>/` (trailing slash) against stored
  `<proj>` (no slash): matched `proj-cmd-55,54` — the current side is normalized
  (trailing separator stripped) before the exact `cwd = ?` comparison. ✅
  - *Minor nuance (non-blocking):* a stored `cwd` value that *itself* contains a
    trailing slash (e.g. a manually-corrupted row) would NOT match, because the SQL
    `WHERE cwd = ?` compares the raw stored string against the normalized current cwd.
    The implementer's caveat "both sides are normalized" is slightly imprecise — only
    the *current* side is normalized; the stored side is exact-matched as-is. This is
    correct for real nushell data (which never has trailing slashes per the research
    report), so it is not a real-world defect, just an imprecise doc statement.

### 5. Plaintext / missing-DB handling — PASS

- **Plaintext-only backend** (created `nushell/history.txt`, no `history.sqlite3`),
  ran `--history-path <…>/nushell/history.sqlite3`:
  ```
  nu-workdir-hist: no SQLite history file found at <…>/nushell/history.sqlite3
  Nushell's default history backend is plaintext (history.txt), which does not store
  the working directory of each command, so filtering by cwd is impossible.

  I found a plaintext history at <…>/nushell/history.txt.

  To use this tool, enable the SQLite backend and migrate your existing history:

      # in config.nu (or $env.config):
      $env.config.history.file_format = "sqlite"

      # then migrate your plaintext history into sqlite (nushell >= 0.100.0):
      history import
  ```
  rc **2**. Message mentions `file_format = "sqlite"` and `history import` and the
  sibling `history.txt`. ✅
- **Missing DB entirely** (`--history-path <…>/does-not-exist.sqlite3`): same actionable
  message (without the "I found a plaintext history" line), rc **2**. ✅

### 6. README documents install, usage, flags, per-OS path, canonicalization, sqlite requirement — PASS

Read the full 117-line `README.md`:

- **Install:** `pipx install` (3 mentions: published name + local checkout) and
  `uv tool install` (2 mentions). ✅
- **Usage:** dedicated `## Usage` section with examples (`-n 100`, `-n 0`, `-v`). ✅
- **Flags:** `### Flags` table covers `-n`/`--last`, `-v`/`--verbose`, `--physical`,
  `--history-path`, `-h`/`--help`, with env-var and default columns. ✅
  (Note: no `--version` row — consistent with the criterion #2 defect.)
- **Per-OS history path:** table with explicit Linux / macOS / Windows rows + note
  that `XDG_CONFIG_HOME` is honored on all platforms. ✅
- **Canonicalization:** dedicated `### Path canonicalization` section explaining
  logical PWD vs `--physical`. ✅
- **SQLite requirement:** `## Requirements` states the SQLite backend is required;
  `### Plaintext backend (not supported)` section gives the migration recipe. ✅

## Defects found

### D1 — `--version` flag is not implemented (minor / blocking-for-this-criterion)

- **Severity:** minor (trivial fix), but it is the only unmet acceptance sub-criterion.
- **Evidence:**
  ```
  $ nu-workdir-hist --version
  usage: nu-workdir-hist [-h] [-n N] [-v] [--physical] [--history-path PATH]
  nu-workdir-hist: error: unrecognized arguments: --version
  $ echo $?
  2
  ```
  `src/nu_workdir_hist/cli.py::build_parser` defines no `--version` argument
  (`grep version src/nu_workdir_hist/cli.py` → none). `src/nu_workdir_hist/__init__.py`
  does define `__version__ = "0.1.0"`; it is simply not exposed to the CLI.
- **Criterion impacted:** #2 ("responds to `--help` and `--version`").
- **Suggested fix (for a follow-up implementation session — not applied here per
  read-only verification):** add to `build_parser()`:
  ```python
  from . import __version__
  p.add_argument("--version", action="version",
                 version=f"%(prog)s {__version__}")
  ```
  (and optionally `-V` as an alias). This is a one-line change with no behavioral risk.

### D2 — Dev-report wording "both sides normalized" is imprecise (non-blocking)

- **Severity:** trivial / documentation only.
- The implementation normalizes only the *current*-cwd side; the stored `cwd` column
  is compared via exact SQL `cwd = ?` (no normalization of the stored value). This is
  correct for real nushell data (research report §3: nushell stores cwd with no
  trailing slash, absolute, no normalization needed on the stored side), so it is not a
  runtime defect — only an imprecise statement in the development report's "Caveats"
  section. No code change needed; the doc statement could be tightened.

## Blockers

None for accepting the package as a working tool. The `--version` gap (D1) is the only
unmet acceptance sub-criterion; it is a one-line fix and does not affect any other
behavior. If strict criterion-by-criterion compliance is required, address D1 before
final acceptance.

## Positive

- Schema fidelity is excellent: `schema.py` reproduces the exact reedline DDL (STRICT
  table, all indexes, `application_id`/`user_version` pragmas), and the tool read my
  independently-built real-schema DB on the first try.
- Read-only access (`file:…?mode=ro`) is correctly applied and explicitly tested
  (`test_query_opens_read_only` asserts writes through the RO connection raise
  `OperationalError`) — addresses the research report's concurrency concern.
- Logical-vs-physical cwd handling is faithful to the research report's finding that
  nushell stores the *logical* PWD (with symlink components), and the `--physical`
  toggle covers the symlinked-physical case cleanly.
- The plaintext/missing-DB error is genuinely actionable (names `file_format`,
  `history import`, and the discovered `history.txt`), matching the research report's
  "Open issues" guidance.
- Test suite covers both unit (arg parsing, path resolution, canonicalization) and
  integration (subprocess `python -m nu_workdir_hist` against a fresh DB) levels.
- README is thorough and accurate to the implemented behavior.

## Recommendation

Accept as **PASS-WITH-ISSUES**. If the orchestrator wants strict criterion #2
compliance, re-delegate a one-line fix to wire `__version__` into the argparse parser
as `--version` (suggested code above). No other remediation is needed. All functional
behavior (querying, filtering, canonicalization, limits, errors, build, install) is
verified correct from independent execution.