"""Path resolution: nushell config dir, history.sqlite3 location, and cwd
canonicalization (logical vs physical).

Nushell stores each command's working directory as its logical `$env.PWD`:
an absolute path with no trailing slashes that *may contain symlink
components* (it is NOT realpath-resolved). See
agent_docs/research/2026-07-16-nushell-history-format.md, section 3.

We match that form by default (logical normalization: absolute + strip
trailing separators). A `--physical` mode resolves the current cwd with
`os.path.realpath` for users whose stored cwd reflects the physical location.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote

__all__ = [
    "default_history_path",
    "resolve_history_path",
    "normalize_logical",
    "normalize_physical",
    "current_workdir",
    "physical_from_env",
]

# Env var names.
NU_HISTORY_PATH_ENV = "NU_HISTORY_PATH"
NU_PHYSICAL_ENV = "NU_WORKDIR_HIST_PHYSICAL"


def _config_dir() -> Path:
    """Resolve nushell's config directory (without the trailing `nushell`).

    Mirrors nushell's `nu_config_dir()` (`crates/nu-path/src/helpers.rs`):
    `$XDG_CONFIG_HOME` wins on *every* platform when set; otherwise the
    OS-specific platform config dir.
    """
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg)

    if sys.platform == "darwin":
        home = os.environ.get("HOME", "")
        return Path(home) / "Library" / "Application Support"
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return Path(appdata)
        # Fall back to USERPROFILE if APPDATA is somehow unset.
        return Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Roaming"
    # Linux and other Unix-likes.
    home = os.environ.get("HOME", "")
    return Path(home) / ".config"


def default_history_path() -> Path:
    """The default `history.sqlite3` path under the nushell config dir."""
    return _config_dir() / "nushell" / "history.sqlite3"


def resolve_history_path(flag_value: str | None) -> Path:
    """Decide which history.sqlite3 to open.

    Priority: explicit `--history-path` flag > `NU_HISTORY_PATH` env var >
    nushell's default config-dir location. An empty string flag/env is treated
    as "not provided".
    """
    if flag_value:  # non-empty string wins
        return Path(flag_value).expanduser()
    env = os.environ.get(NU_HISTORY_PATH_ENV)
    if env:
        return Path(env).expanduser()
    return default_history_path()


# ---------------------------------------------------------------- cwd


def _strip_trailing_sep(abs_path: str) -> str:
    """Remove a single trailing separator, preserving the root path.

    Nushell's PWD has no trailing slash except for the root itself (e.g. `/`).
    """
    # os.path.splitdrive gives ('C:', '\\foo') on Windows; we keep the drive.
    drive, tail = os.path.splitdrive(abs_path)
    if tail in ("", os.sep, "/"):
        # Root of the (drive's) filesystem: keep one separator.
        return drive + os.sep if drive else os.sep
    if tail.endswith(os.sep) or tail.endswith("/"):
        tail = tail.rstrip(os.sep).rstrip("/")
        if tail == "":
            return drive + os.sep if drive else os.sep
    return drive + tail


def normalize_logical(path: Path | str) -> str:
    """Normalize a path the way nushell stores `cwd`: absolute, no trailing slash.

    Does NOT resolve symlinks — this matches nushell's logical `$env.PWD`.
    A relative path is resolved against the process cwd (as `cd` would).
    """
    p = Path(path)
    if not p.is_absolute():
        p = Path.cwd() / p
    return _strip_trailing_sep(str(p))


def normalize_physical() -> str:
    """Resolve the current working directory with realpath (symlinks resolved)."""
    return _strip_trailing_sep(os.path.realpath(os.getcwd()))


def current_workdir(*, physical: bool) -> str:
    """The cwd string to match stored `cwd` values against.

    In logical mode we prefer nushell's logical PWD from the ``$PWD`` env var
    when it is set and absolute: ``os.getcwd()``/``Path.cwd()`` return the
    *physical* path on Linux (resolving symlinks left by ``chdir``), whereas
    nushell records the logical PWD it keeps in ``$env.PWD``. Using ``$PWD``
    keeps the two sides comparable when the user runs the tool from the same
    logical path nushell was in. Falls back to the physical cwd when ``$PWD``
    is absent or relative.
    """
    if physical:
        return normalize_physical()
    pwd_env = os.environ.get("PWD")
    if pwd_env and Path(pwd_env).is_absolute():
        return _strip_trailing_sep(pwd_env)
    return normalize_logical(Path.cwd())


def physical_from_env(value: str | None) -> bool:
    """Interpret the `NU_WORKDIR_HIST_PHYSICAL` env var truthily."""
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}