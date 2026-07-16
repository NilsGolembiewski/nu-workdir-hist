# nu-workdir-hist

List nushell command-history entries that were executed in the current working directory.

`nu-workdir-hist` reads nushell's SQLite command history (`history.sqlite3`) and
prints the commands that were run from the directory you invoke it in, most-recent
first.

## Requirements

- A nushell installation using the **SQLite** history backend
  (`$env.config.history.file_format = "sqlite"`).
- Python 3.10+.

The default nushell history backend is **plaintext** (`history.txt`), which does
**not** record the working directory of each command. This tool requires the
SQLite backend. If only `history.txt` is found, the tool prints an actionable
error explaining how to switch and migrate (see
[Plaintext backend](#plaintext-backend-not-supported) below).

## Installation

```console
# with pipx
pipx install nu-workdir-hist

# from a local checkout
pipx install /path/to/nu-workdir-hist

# with uv
uv tool install nu-workdir-hist
uv tool install /path/to/nu-workdir-hist
```

This installs a `nu-workdir-hist` command on your `PATH`.

## Usage

```console
$ cd ~/projects/my-app
$ nu-workdir-hist          # last 50 commands run from this directory
$ nu-workdir-hist -n 100   # last 100
$ nu-workdir-hist -n 0     # all of them (no limit)
$ nu-workdir-hist -v       # include timestamp + exit status
```

### Flags

| Flag | Env var | Default | Description |
| --- | --- | --- | --- |
| `-n N`, `--last N` | `NU_WORKDIR_HIST_LAST` | `50` | Number of commands to print (most-recent first). `0` = no limit / print all. Negative values are rejected. |
| `-v`, `--verbose` | — | off | Also print the start timestamp and exit status for each command. |
| `--physical` | `NU_WORKDIR_HIST_PHYSICAL=1` | off | Resolve the current working directory with `os.path.realpath` (symlink-resolved / physical path) before matching. Use this if you browse through symlinks and the stored `cwd` reflects the physical location. |
| `--history-path PATH` | `NU_HISTORY_PATH` | nushell default | Path to `history.sqlite3`. Overrides the per-OS config-dir resolution. |
| `-h`, `--help` | — | — | Show help. |

### History file location

By default the tool resolves nushell's config directory per OS and appends
`history.sqlite3`:

| OS | Default `history.sqlite3` location |
| --- | --- |
| Linux | `$XDG_CONFIG_HOME/nushell/history.sqlite3` or `~/.config/nushell/history.sqlite3` |
| macOS | `~/Library/Application Support/nushell/history.sqlite3` (or `$XDG_CONFIG_HOME/nushell/...` if `XDG_CONFIG_HOME` is set) |
| Windows | `%APPDATA%\nushell\history.sqlite3` |

`XDG_CONFIG_HOME` is honored on **all** platforms when set. Override the path with
`--history-path` or `NU_HISTORY_PATH` (the latter is handy for users who set a
custom `$env.config.history.path` in nushell 0.112.1+).

### Path canonicalization

Nushell stores each command's working directory as its **logical** `$env.PWD` —
an absolute path with no trailing slashes that **may contain symlink
components** (it is *not* `realpath`-resolved). `nu-workdir-hist` normalizes both
sides the same way: the directory the tool is run in and the stored `cwd` are
made absolute with trailing separators stripped, then compared exactly. This
matches nushell's logical-PWD form and works as long as you run the tool from
the same logical path nushell recorded.

If you navigate via symlinks and the stored `cwd` reflects the physical
location, pass `--physical` (or set `NU_WORKDIR_HIST_PHYSICAL=1`) to resolve the
current directory with `os.path.realpath` before comparison.

### Plaintext backend (not supported)

If `history.sqlite3` is absent but `history.txt` is present, the tool prints
something like:

```
nu-workdir-hist: no SQLite history file found at /home/me/.config/nushell/history.sqlite3
Nushell's default history backend is plaintext (history.txt), which does not store
the working directory of each command, so filtering by cwd is impossible.

To use this tool, enable the SQLite backend and migrate your existing history:

    # in config.nu (or $env.config):
    $env.config.history.file_format = "sqlite"

    # then migrate your plaintext history into sqlite (nushell >= 0.100.0):
    history import
```

and exits with a non-zero status.

## Development

```console
uv sync                 # install dev dependencies
uv run pytest           # run tests
uv build                # build sdist + wheel
pipx install --force .  # install locally for manual testing
```

## License

MIT