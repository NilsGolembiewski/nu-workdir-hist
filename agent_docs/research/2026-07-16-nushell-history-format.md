# Research: Nushell command history storage format & schema (cwd association)

**Date:** 2026-07-16
**Scope:** Determine the exact storage format and schema of nushell's command history — file path per OS, sqlite schema, the column holding the command, the column holding the cwd, how cwd is represented/stored, and version differences across nushell 0.90+. Output is a research report only (no tool built).

## Outcome

success

## Summary

Nushell delegates command history to **reedline**, its line-editor crate. There are **two** history backends, selectable via `$env.config.history.file_format`:

- `"plaintext"` → `history.txt` (one command per line, **no cwd**, no metadata). This is the **default** on current `main` (`HistoryFileFormat::Plaintext` in `HistoryConfig::default()`; `doc_config.nu` documents `Default: "plaintext"`).
- `"sqlite"` → `history.sqlite3`, a SQLite database with a single `history` table that **does** record the per-command working directory in a `cwd` (TEXT) column.

The sqlite schema is stable and single-table. The cwd is stored as a **string** equal to nushell's `$env.PWD` at the time the command was executed — an **absolute path with no trailing slashes** (root path excepted), which **may contain symlink components** (i.e. it is the logical PWD, NOT a `realpath`/`canonicalize`-resolved physical path). It is written to the row *after* the command is saved, via reedline's `update_last_command_context` mechanism (nushell calls `prepare_history_metadata` → `update_last_command_context`, then `fill_in_result_related_history_metadata` after execution).

For a CLI that filters history by cwd, the sqlite backend is the only usable one; the plaintext backend does not store cwd at all.

## Key findings

### 1. Default history file path per OS

Nushell resolves the history file from the **config directory** (`$nu.default-config-dir`), then appends the backend's default file name (`history.txt` or `history.sqlite3`). The config directory is resolved as follows (see `crates/nu-path/src/helpers.rs::nu_config_dir()` and the `directories`/`etcetera` conventions nushell uses, plus the documented behavior in `book/configuration.md`):

1. If `$env.XDG_CONFIG_HOME` is set (on **any** OS) → use `$env.XDG_CONFIG_HOME/nushell`.
2. Otherwise, use the OS-specific config dir (via the `dirs`/`directories` crate's `config_dir()`):
   - **Linux:** `$XDG_CONFIG_HOME` or `$HOME/.config` → `<…>/nushell/history.sqlite3` (e.g. `/home/me/.config/nushell/history.sqlite3`)
   - **macOS:** `$HOME/Library/Application Support/nushell/history.sqlite3` (the `directories` crate returns `~/Library/Application Support` as `config_dir` on macOS). *Note: there was long discussion (issue #12103, PR #8682) about also supporting `~/.config/nushell` on macOS, and `XDG_CONFIG_HOME` is now honored on all platforms; if a user has `XDG_CONFIG_HOME` set they get that location regardless of OS.*
   - **Windows:** `%APPDATA%\Roaming\nushell\history.sqlite3` → resolves to `C:\Users\me\AppData\Roaming\nushell\history.sqlite3` (the `directories` crate's `config_dir` = `{FOLDERID_RoamingAppData}` = `%APPDATA%`). **Not** `%LOCALAPPDATA%`.

So the full default sqlite history path:

| OS | Default sqlite history path (when `file_format: sqlite`) |
| --- | --- |
| Linux | `$XDG_CONFIG_HOME/nushell/history.sqlite3` or `~/.config/nushell/history.sqlite3` |
| macOS | `~/Library/Application Support/nushell/history.sqlite3` (unless `XDG_CONFIG_HOME` is set, then `$XDG_CONFIG_HOME/nushell/history.sqlite3`) |
| Windows | `%APPDATA%\nushell\history.sqlite3` (i.e. `C:\Users\me\AppData\Roaming\nushell\history.sqlite3`) |

Override knobs:
- `$env.config.history.path` (added in **0.112.1**, see blog/2026-04-11): a custom path; `null` disables history entirely; an empty string means "use default"; a bare filename is stored under `$nu.default-config-dir`; a directory path gets the default file name (`history.txt`/`history.sqlite3`) appended. (Code: `crates/nu-protocol/src/config/history.rs::HistoryConfig::file_path`.)
- `$env.config.history.file_format` selects `history.txt` vs `history.sqlite3`.

The python tool should resolve the path as: prefer `$env.config.history.path` (but reading the user's nushell config from python is heavy); a robust default is to look in `$nu.default-config-dir` (i.e. `XDG_CONFIG_HOME|~/.config|~/Library/Application Support|%APPDATA%` + `/nushell/history.sqlite3`). Document that users may have customized `history.path`.

### 2. The sqlite schema (CREATE TABLE) and column meanings

Source: `nushell/reedline` `src/history/sqlite_backed.rs` (`SqliteBackedHistory::from_connection`). The exact DDL (run inside `db.execute_batch`) is:

```sql
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
create index if not exists idx_history_cwd on history(cwd); -- suboptimal for many hosts
create index if not exists idx_history_exit_status on history(exit_status);
create index if not exists idx_history_cmd on history(command_line);
create index if not exists idx_history_cmd on history(session_id);
-- todo: better indexes
```

Database-level metadata set at creation:
- `PRAGMA application_id = 1151497937` (constant `SQLITE_APPLICATION_ID`).
- `PRAGMA user_version = 0` is required (the loader errors with "Unknown database version {db_version}" if `user_version != 0`).
- `PRAGMA journal_mode = wal`, `synchronous = normal`, `mmap_size = 1000000000`, `foreign_keys = on`.

Column meanings (the **exact column names** matter for the tool):

| Column | Type | Meaning |
| --- | --- | --- |
| `id` | INTEGER PK autoincrement | Monotonically increasing row id. Newer commands have higher ids. **Best column to order by for chronological/recency order.** |
| `command_line` | TEXT NOT NULL | **The command text.** This is the field you want to list. |
| `start_timestamp` | INTEGER | When the command was entered, as **milliseconds since the Unix epoch** (UTC). Stored via `chrono::DateTime::timestamp_millis()`. May be NULL for entries without metadata. |
| `session_id` | INTEGER | reedline history session id (per-shell-session grouping when `history.isolation` is on). May be NULL. |
| `hostname` | TEXT | Hostname of the machine the command ran on. May be NULL. |
| **`cwd`** | TEXT | **The working directory the command was executed in.** May be NULL (e.g. plaintext-imported entries, or rows updated before nushell's metadata step). |
| `duration_ms` | INTEGER | Command duration in milliseconds. May be NULL. |
| `exit_status` | INTEGER | Exit code. `0` = success; may be NULL. |
| `more_info` | TEXT | JSON-serialized `HistoryItemExtraInfo`. May be NULL. |

Important names to remember: **command text = `command_line`**, **cwd = `cwd`**. (There is no `cwd_str` column. The nushell `history` command itself aliases `command_line AS command` and `duration_ms AS duration` in its SELECT, but the underlying columns are `command_line` and `cwd`.)

### 3. How cwd is stored (string form / canonicalization)

The `cwd` column is a **TEXT** string. Nushell populates it via `prepare_history_metadata` in `crates/nu-cli/src/repl.rs`:

```rust
c.cwd = engine_state.cwd(None).ok().map(|path| path.to_string_lossy().to_string());
```

`EngineState::cwd()` (in `crates/nu-protocol/src/engine/engine_state.rs`) returns nushell's `$env.PWD` as an `AbsolutePathBuf`. Its docstring is explicit:

> "Returns the current working directory, which is guaranteed to be an absolute path without trailing slashes (unless it's the root path), but might contain symlink components."

So the stored `cwd` is:
- An **absolute** path (never relative).
- **No trailing slash** (except the root path itself, e.g. `/`).
- **Logical** PWD — it is **NOT** symlink-resolved via `std::fs::canonicalize`/`realpath`. If a user is in a directory reached through a symlink, the stored cwd contains the symlink component (matching whatever nushell's `$env.PWD` held). Nushell maintains `$env.PWD` consistently on `cd` and at startup (set from the process cwd), and rejects PWD values that are non-absolute, have trailing slashes, don't exist, or aren't directories.
- On Windows it uses native separators within the string as nushell produced them (e.g. `C:\Users\me\proj`).

**Implication for the python tool:** to match "commands executed in the current working directory", compare `cwd` against the **current directory as nushell would see it** — i.e. an absolute, no-trailing-slash path. Best approach: canonicalize neither side strictly, but normalize: make absolute + strip trailing separators, and be aware symlinked dirs may differ from `os.path.realpath()` results. Matching on the raw absolute form (nushell's PWD) is the most faithful comparison. Consider also exposing a `--prefix`/subdir mode since reedline itself supports `cwd_prefix` filtering (`cwd LIKE :cwd_like`).

### 4. Version differences (0.90+)

- **History backends:** `history.file_format` has long supported `"sqlite"` and `"plaintext"`. SQLite history (with cwd/timestamps/exit_status) has existed since well before 0.90 (reedline's `SqliteBackedHistory`). **Plaintext is still the default** on current `main` (`HistoryFileFormat::Plaintext` in `Default for HistoryConfig`; `crates/nu-utils/src/default_files/doc_config.nu` documents `Default: "plaintext"`). There is an **open** effort (issue #14282, earlier PR #10440) to flip the default to sqlite, but as of the sources reviewed it has not landed. **Many real users set `file_format: sqlite` manually** (the docs and blog posts recommend it), so a tool should detect the backend and gracefully inform plaintext users that cwd filtering requires sqlite.
- **File names:** sqlite → `history.sqlite3`; plaintext → `history.txt` (see `HistoryFileFormat::default_file_name()`).
- **`$env.config.history.path`** was added in **0.112.1** (blog 2026-04-11-nushell_v0_112_1). Before this, the history file was always `<config_dir>/<history.txt|history.sqlite3>` with no override. The python tool should support a custom path via env/config but default to the config-dir resolution.
- **`history import`** command (added 0.100.0, blog 2024-11-12) lets users migrate `history.txt` → `history.sqlite3` (and vice versa). This is the recommended migration path for plaintext users who want cwd data.
- **Schema versioning:** the sqlite DB uses `PRAGMA user_version`, which reedline currently requires to be exactly `0`. The schema itself (the `history` table above) has been stable across the 0.90+ range; there is no separate schema-version migration in the current code (any non-zero `user_version` is rejected as an error, not migrated). So a tool can assume the single `history` table with the columns listed above for any sqlite history file produced by nushell 0.90–0.112+.
- **`strict` tables:** the `history` table is created `STRICT`, which enforces column types. This doesn't affect read access but is worth noting if the tool ever writes.

### 5. Representative SELECT queries

Given the real column names (`command_line` for the command, `cwd` for the working directory, `id` for monotonic ordering, `start_timestamp` for time-based ordering):

Most-recent-first list of commands executed in a given cwd (filter by exact cwd):

```sql
SELECT command_line, cwd, start_timestamp, exit_status
FROM history
WHERE cwd = ?
ORDER BY id DESC
LIMIT ?;
```

Oldest-first (chronological):

```sql
SELECT command_line, cwd, start_timestamp
FROM history
WHERE cwd = ?
ORDER BY id ASC
LIMIT ?;
```

Time-based ordering alternative (start_timestamp is ms-since-epoch; note it can be NULL):

```sql
SELECT command_line, cwd
FROM history
WHERE cwd = ?
ORDER BY start_timestamp DESC
LIMIT ?;
```

Prefix/subdirectory match (commands whose cwd is under a given path, like reedline's `cwd_prefix` filter):

```sql
SELECT command_line, cwd
FROM history
WHERE cwd LIKE ?   -- bind param should be '<prefix>%'
ORDER BY id DESC
LIMIT ?;
```

Dedup tip: to avoid showing consecutive duplicates (reedline's FileBackedHistory skips dupes, but sqlite keeps them), you can use a window function or `GROUP BY command_line` if desired — but nushell's own `history` command keeps duplicates and orders by `id`, so matching that behavior (simple `ORDER BY id DESC`) is the closest to user expectation.

The index `idx_history_cwd` exists on `history(cwd)`, so `WHERE cwd = ?` and `cwd LIKE '<prefix>%'` are both index-backed.

## Citations

- reedline `src/history/sqlite_backed.rs` — `CREATE TABLE history` DDL, indexes, `user_version`/`application_id` pragmas, `deserialize_history_item`, `save` (`INSERT ... ON CONFLICT DO UPDATE ... RETURNING id`):
  https://github.com/nushell/reedline/blob/main/src/history/sqlite_backed.rs
- reedline `src/engine.rs` — `Reedline::with_cwd`, `has_last_command_context`, `update_last_command_context` (→ `history.update`), the `read_line` accept path that saves `HistoryItem::from_command_line` then lets the host fill metadata; `last_with_prefix_and_cwd` / `cwd_prefix` search filters:
  https://github.com/nushell/reedline/blob/main/src/engine.rs
- reedline `src/history/base.rs` / `src/history/item.rs` — `HistoryItem` fields (`command_line`, `cwd`, `start_timestamp`, `duration`, `exit_status`, `more_info`), `from_command_line`:
  https://github.com/nushell/reedline/blob/main/src/history/item.rs
- nushell `crates/nu-cli/src/repl.rs` — `prepare_history_metadata` (sets `c.cwd = engine_state.cwd(None)...`), `fill_in_result_related_history_metadata` (sets duration/exit_status), `with_cwd(... engine_state.cwd(None) ...)` on the line editor, `setup_history`, `store_history_id_in_engine`:
  https://github.com/nushell/nushell/blob/main/crates/nu-cli/src/repl.rs
- nushell `crates/nu-protocol/src/engine/engine_state.rs` — `EngineState::cwd()` docstring ("absolute path without trailing slashes ... might contain symlink components") and `cwd_as_string`:
  https://github.com/nushell/nushell/blob/main/crates/nu-protocol/src/engine/engine_state.rs
- nushell `crates/nu-protocol/src/config/history.rs` — `HistoryFileFormat::default_file_name` (`history.txt` / `history.sqlite3`), `HistoryConfig::default()` (plaintext default), `HistoryPath` (Default/Custom/Disabled), `HistoryConfig::file_path()`:
  https://github.com/nushell/nushell/blob/main/crates/nu-protocol/src/config/history.rs
- nushell `crates/nu-path/src/helpers.rs` — `nu_config_dir()` (XDG_CONFIG_HOME-or-OS-config-dir + "nushell"), `data_dir()`:
  https://github.com/nushell/nushell/blob/main/crates/nu-path/src/helpers.rs
- nushell `crates/nu-cli/src/commands/history/history_.rs` — nushell's own `history` command SELECT (`command_line as command`, `cwd`, `duration_ms as duration`, `id`/`rowid` ordering, `path_columns: ["cwd"]`):
  https://github.com/nushell/nushell/blob/main/crates/nu-cli/src/commands/history/history_.rs
- nushell `crates/nu-utils/src/default_files/doc_config.nu` — documents `history.file_format` default = `"plaintext"`, `history.path` semantics:
  https://github.com/nushell/nushell/blob/main/crates/nu-utils/src/default_files/doc_config.nu
- Nushell configuration docs — `$nu.default-config-dir` per-OS examples (Linux `~/.config/nushell`, macOS `~/Library/Application Support/nushell`, Windows `C:\Users\me\AppData\Roaming\nushell`), XDG_CONFIG_HOME honored on all platforms, history stored in config dir by default:
  https://www.nushell.sh/book/configuration.html
- `directories` crate docs (the conventions nushell follows: `config_dir` = `$XDG_CONFIG_HOME`/`~/.config` on Linux, `RoamingAppData` on Windows, `~/Library/Application Support` on macOS):
  https://docs.rs/directories/latest/directories/
- Nushell 0.112.1 release blog — addition of `$env.config.history.path` (null disables history, custom path supported):
  https://github.com/nushell/nushell.github.io/blob/main/blog/2026-04-11-nushell_v0_112_1.md
- Nushell 0.100.0 release blog — `history import` command (migrate plaintext↔sqlite):
  https://github.com/nushell/nushell.github.io/blob/main/blog/2024-11-12-nushell_0_100_0.md
- Issue #14282 "Enable SQLite-backed history by default" (open; default still plaintext):
  https://github.com/nushell/nushell/issues/14282
- PR #10440 (earlier attempt to make sqlite default; closed without merging):
  https://github.com/nushell/nushell/pull/10440
- Issue #12103 / PR #8682 (XDG_CONFIG_HOME honored on all platforms; macOS default-location debate):
  https://github.com/nushell/nushell/issues/12103

## Open issues

- **Plaintext is the default backend and stores no cwd.** The tool should detect `history.sqlite3` presence; if only `history.txt` exists, cwd filtering is impossible — surface a clear message and point users at `$env.config.history.file_format = "sqlite"` + `history import`.
- **Custom `history.path`** (0.112.1+) means the sqlite file may live anywhere. A python CLI can't easily read the user's `config.nu`; consider an env var / CLI flag override (e.g. `NU_HISTORY_PATH`) and otherwise default to the config-dir resolution above. Reading `$nu.default-config-dir` programmatically requires replicating the XDG/OS logic (done above).
- **Symlink semantics:** stored cwd is logical PWD, not `realpath`. If the tool computes "current working directory" via `os.getcwd()`/`Path.cwd()` it will get the physical path, which may differ from nushell's logical PWD for symlinked dirs. Consider normalizing both sides to absolute + strip trailing separators, and optionally offer a `--physical`/`--logical` toggle or fall back to prefix matching to be tolerant. Exact-match on nushell's logical PWD form is the most correct default.
- **`cwd` can be NULL** for some rows (e.g. imported from plaintext, or if metadata update failed). Queries should filter `WHERE cwd IS NOT NULL` when counting, or accept NULLs as "not matching".
- **Concurrent access:** the DB is opened with WAL journaling; reading it from python while nushell is running is generally safe (WAL supports concurrent readers), but the tool should open read-only (`?mode=ro`) to avoid locking surprises.
- **Schema version stability:** only `user_version = 0` is currently accepted by reedline. If a future nushell bumps the schema version, the tool's assumptions (column names) should be re-validated; the columns above hold for all 0.90–0.112+ versions surveyed.