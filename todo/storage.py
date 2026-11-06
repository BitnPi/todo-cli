"""JSON file persistence for todos."""

import json
import os
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # not available on Windows
    fcntl = None

DEFAULT_PATH = "todos.json"
ENV_VAR = "TODO_FILE"

Todo = dict[str, Any]


class StorageError(Exception):
    """The todo file could not be understood."""


def todo_path() -> Path:
    """Return the todo file path, honouring ``TODO_FILE`` when it is set."""
    return Path(os.environ.get(ENV_VAR) or DEFAULT_PATH)


def _real_path(path: Path) -> Path:
    """Follow symlinks in ``path``, so writes reach the real file.

    os.replace() would otherwise swap out a symlink instead of updating its
    target. Components that don't exist yet are kept as they are, so this also
    works for a file still to be created, including through a dangling symlink.
    Unlike Path.resolve() before Python 3.13, realpath() doesn't raise
    RuntimeError on a symlink loop; that surfaces as an OSError on first use.
    """
    return Path(os.path.realpath(path))


@contextmanager
def locked(path: Path) -> Iterator[None]:
    """Hold an exclusive lock on ``path`` for a whole load -> mutate -> save cycle.

    save() is atomic, but that only prevents partial files: without this lock,
    two writers can load the same list and the last save drops the other's
    change. Readers don't need it, because save() never exposes partial data.

    The lock lives on a sibling ``<path>.lock`` because save() replaces the todo
    file's inode, so a lock on the file itself would be left behind on the old
    one. The lock file is deliberately never removed: unlinking it would let two
    processes hold "the" lock on different inodes. The lock isn't reentrant.
    Symlinks are resolved first, so every path to the same file shares one lock.

    Where fcntl is missing (Windows) this does nothing, so concurrent writers
    there can still lose updates.
    """
    path = _real_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.parent / f"{path.name}.lock", "a") as lock_file:
        if fcntl is not None:
            # Released when the file is closed, including if the process dies.
            fcntl.flock(lock_file, fcntl.LOCK_EX)
        yield


def _is_valid(item: Any) -> bool:
    return (
        isinstance(item, dict)
        # bool is a subclass of int, so it has to be excluded explicitly.
        and type(item.get("id")) is int
        and isinstance(item.get("text"), str)
        and isinstance(item.get("done"), bool)
    )


def load(path: Path) -> list[Todo]:
    """Read todos from ``path``; a file that does not exist yet means no todos."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except ValueError as exc:  # invalid JSON or invalid UTF-8
        raise StorageError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, list) or not all(_is_valid(item) for item in data):
        raise StorageError(
            f"{path} must be a list of objects with integer id, "
            "string text and bool done"
        )
    return data


def _file_mode(path: Path) -> int:
    """Return the mode ``path`` should have: its current one, else the umask default."""
    try:
        return stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        umask = os.umask(0)
        os.umask(umask)
        return 0o666 & ~umask


def save(path: Path, todos: list[Todo]) -> None:
    """Write todos atomically so a failed write cannot corrupt existing data.

    Each save writes to its own exclusively created temp file, so concurrent
    saves cannot touch each other's pending data or any unrelated file.
    """
    path = _real_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(json.dumps(todos, indent=2, ensure_ascii=False) + "\n")
        # mkstemp creates the file 0600; don't let that leak onto the todo file.
        tmp.chmod(_file_mode(path))
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def next_id(todos: list[Todo]) -> int:
    """Return one more than the highest existing id, starting at 1."""
    return max((todo["id"] for todo in todos), default=0) + 1
