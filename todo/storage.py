"""JSON file persistence for todos."""

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_PATH = "todos.json"
ENV_VAR = "TODO_FILE"

Todo = dict[str, Any]


class StorageError(Exception):
    """The todo file could not be understood."""


def todo_path() -> Path:
    """Return the todo file path, honouring ``TODO_FILE`` when it is set."""
    return Path(os.environ.get(ENV_VAR) or DEFAULT_PATH)


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


def save(path: Path, todos: list[Todo]) -> None:
    """Write todos atomically so a failed write cannot corrupt existing data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(
            json.dumps(todos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def next_id(todos: list[Todo]) -> int:
    """Return one more than the highest existing id, starting at 1."""
    return max((todo["id"] for todo in todos), default=0) + 1
