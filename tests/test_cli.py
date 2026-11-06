"""Tests for the add, list and done commands."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from todo import storage
from todo.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, todos):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(todos), encoding="utf-8")


def spawn(path, *args):
    """Start a real ``todo`` process against ``path`` without waiting for it."""
    return subprocess.Popen(
        [sys.executable, "-m", "todo.cli", *args],
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT), "TODO_FILE": str(path)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


# add


def test_add_prints_id_and_persists_schema(todo_file, capsys):
    assert main(["add", "buy milk"]) == 0
    assert capsys.readouterr().out == "1\n"
    assert read(todo_file) == [{"id": 1, "text": "buy milk", "done": False}]


def test_add_joins_unquoted_words(todo_file):
    assert main(["add", "buy", "milk"]) == 0
    assert read(todo_file)[0]["text"] == "buy milk"


def test_add_increments_ids(todo_file, capsys):
    main(["add", "one"])
    main(["add", "two"])
    assert capsys.readouterr().out == "1\n2\n"
    assert [todo["id"] for todo in read(todo_file)] == [1, 2]


def test_add_uses_max_existing_id_plus_one(todo_file, capsys):
    write(
        todo_file,
        [
            {"id": 7, "text": "high", "done": True},
            {"id": 2, "text": "low", "done": False},
        ],
    )
    assert main(["add", "next"]) == 0
    assert capsys.readouterr().out == "8\n"


def test_add_preserves_non_ascii_text(todo_file, capsys):
    main(["add", "café ☕"])
    capsys.readouterr()
    assert "café ☕" in todo_file.read_text(encoding="utf-8")
    main(["list"])
    assert capsys.readouterr().out == "1: [ ] café ☕\n"


def test_add_rejects_blank_text(todo_file, capsys):
    assert main(["add", "   "]) == 1
    assert "empty" in capsys.readouterr().err
    assert not todo_file.exists()


def test_add_requires_text(todo_file):
    with pytest.raises(SystemExit) as exc:
        main(["add"])
    assert exc.value.code != 0


# list


def test_list_without_file_prints_nothing(todo_file, capsys):
    assert main(["list"]) == 0
    assert capsys.readouterr().out == ""
    assert not todo_file.exists()


def test_list_formats_open_and_done_items(todo_file, capsys):
    write(
        todo_file,
        [
            {"id": 1, "text": "open", "done": False},
            {"id": 2, "text": "finished", "done": True},
        ],
    )
    assert main(["list"]) == 0
    assert capsys.readouterr().out == "1: [ ] open\n2: [x] finished\n"


# done


def test_done_marks_only_the_given_item(todo_file, capsys):
    main(["add", "one"])
    main(["add", "two"])
    capsys.readouterr()
    assert main(["done", "2"]) == 0
    assert [todo["done"] for todo in read(todo_file)] == [False, True]
    main(["list"])
    assert capsys.readouterr().out == "1: [ ] one\n2: [x] two\n"


def test_done_is_idempotent(todo_file):
    main(["add", "one"])
    assert main(["done", "1"]) == 0
    assert main(["done", "1"]) == 0
    assert read(todo_file)[0]["done"] is True


def test_done_missing_id_fails_and_leaves_file_unchanged(todo_file, capsys):
    main(["add", "one"])
    before = todo_file.read_bytes()
    capsys.readouterr()
    assert main(["done", "99"]) == 1
    captured = capsys.readouterr()
    assert "99" in captured.err
    assert captured.out == ""
    assert todo_file.read_bytes() == before


def test_done_with_no_file_fails(todo_file):
    assert main(["done", "1"]) == 1
    assert not todo_file.exists()


def test_done_non_integer_id_fails(todo_file):
    with pytest.raises(SystemExit) as exc:
        main(["done", "abc"])
    assert exc.value.code != 0


# file location


def test_default_path_is_todos_json_in_cwd(tmp_path):
    assert main(["add", "here"]) == 0
    assert read(tmp_path / "todos.json")[0]["text"] == "here"


def test_todo_file_override_is_used_instead_of_default(tmp_path, todo_file):
    assert main(["add", "elsewhere"]) == 0
    assert read(todo_file)[0]["text"] == "elsewhere"
    assert not (tmp_path / "todos.json").exists()


def test_empty_todo_file_falls_back_to_default(tmp_path, monkeypatch):
    monkeypatch.setenv("TODO_FILE", "")
    assert main(["add", "here"]) == 0
    assert (tmp_path / "todos.json").exists()


# errors and usage


@pytest.mark.parametrize("command", [["list"], ["add", "x"], ["done", "1"]])
def test_corrupt_file_reports_error_and_is_not_overwritten(todo_file, capsys, command):
    todo_file.parent.mkdir(parents=True)
    todo_file.write_text("{not json", encoding="utf-8")
    assert main(command) == 1
    assert "not valid JSON" in capsys.readouterr().err
    assert todo_file.read_text(encoding="utf-8") == "{not json"


def test_os_error_is_reported_cleanly(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TODO_FILE", str(tmp_path))  # a directory, not a file
    assert main(["list"]) == 1
    assert capsys.readouterr().err.startswith("todo: ")


def test_no_command_prints_usage(capsys):
    assert main([]) == 0
    assert "usage: todo" in capsys.readouterr().out


def test_process_exit_codes(tmp_path):
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT),
        "TODO_FILE": str(tmp_path / "t.json"),
    }

    def run(*args):
        return subprocess.run(
            [sys.executable, "-m", "todo.cli", *args],
            env=env,
            capture_output=True,
            text=True,
        )

    assert run("add", "one").stdout == "1\n"
    assert run("done", "1").returncode == 0
    assert run("list").stdout == "1: [x] one\n"
    assert run("done", "2").returncode != 0


# symlinks


@pytest.fixture
def linked(tmp_path):
    """Return ``(link, target)``, with the symlink in a different directory."""
    target = tmp_path / "real" / "t.json"
    link = tmp_path / "links" / "t.json"
    target.parent.mkdir()
    link.parent.mkdir()
    link.symlink_to(target)
    return link, target


@pytest.mark.parametrize("command", [("add", "new"), ("done", "1")])
def test_modifying_commands_update_symlink_target(linked, monkeypatch, command):
    link, target = linked
    write(target, [{"id": 1, "text": "first", "done": False}])
    monkeypatch.setenv("TODO_FILE", str(link))

    assert main(list(command)) == 0

    assert link.is_symlink()
    assert read(link) == read(target)
    assert read(target) != [{"id": 1, "text": "first", "done": False}]


def test_add_through_dangling_symlink_creates_target(linked, monkeypatch):
    link, target = linked
    monkeypatch.setenv("TODO_FILE", str(link))

    assert main(["add", "new"]) == 0

    assert link.is_symlink()
    assert read(target) == [{"id": 1, "text": "new", "done": False}]


def test_add_through_symlinked_parent_creates_file(tmp_path, monkeypatch):
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "alias").symlink_to(real, target_is_directory=True)
    monkeypatch.setenv("TODO_FILE", str(tmp_path / "alias" / "t.json"))

    assert main(["add", "new"]) == 0

    assert read(real / "t.json") == [{"id": 1, "text": "new", "done": False}]


def test_symlink_and_target_share_one_lock(linked):
    link, target = linked

    with storage.locked(target):
        process = spawn(link, "add", "new")
        with pytest.raises(subprocess.TimeoutExpired):
            process.wait(timeout=1)

    _, stderr = process.communicate(timeout=30)
    assert process.returncode == 0, stderr
    assert read(target) == [{"id": 1, "text": "new", "done": False}]


def test_symlink_loop_is_reported_cleanly(tmp_path, monkeypatch, capsys):
    loop = tmp_path / "loop.json"
    loop.symlink_to(loop)
    monkeypatch.setenv("TODO_FILE", str(loop))

    assert main(["add", "new"]) != 0
    assert capsys.readouterr().err


# concurrency


@pytest.mark.parametrize("command", [("add", "new"), ("done", "1")])
def test_modifying_commands_load_only_after_taking_the_lock(tmp_path, command):
    path = tmp_path / "t.json"
    first = {"id": 1, "text": "first", "done": False}
    second = {"id": 2, "text": "second", "done": False}
    write(path, [first])

    with storage.locked(path):
        process = spawn(path, *command)
        with pytest.raises(subprocess.TimeoutExpired):
            process.wait(timeout=1)
        # Written while the command waits: it must see this, not a stale list.
        write(path, [first, second])

    _, stderr = process.communicate(timeout=30)
    assert process.returncode == 0, stderr
    todos = read(path)
    assert second in todos
    assert len(todos) == (3 if command[0] == "add" else 2)


def test_concurrent_adds_keep_every_item_with_unique_ids(tmp_path):
    path = tmp_path / "t.json"
    count = 24
    processes = [spawn(path, "add", f"item {i}") for i in range(count)]
    results = [process.communicate(timeout=60) for process in processes]

    assert all(process.returncode == 0 for process in processes), results
    todos = read(path)
    assert sorted(todo["text"] for todo in todos) == sorted(
        f"item {i}" for i in range(count)
    )
    assert sorted(todo["id"] for todo in todos) == list(range(1, count + 1))
    assert sorted(int(stdout) for stdout, _ in results) == list(range(1, count + 1))


def test_concurrent_add_and_done_keep_both_changes(tmp_path):
    path = tmp_path / "t.json"
    count = 12
    write(path, [{"id": i, "text": "old", "done": False} for i in range(1, count + 1)])

    processes = [spawn(path, "done", str(i)) for i in range(1, count + 1)]
    processes += [spawn(path, "add", f"new {i}") for i in range(count)]
    results = [process.communicate(timeout=60) for process in processes]

    assert all(process.returncode == 0 for process in processes), results
    todos = read(path)
    assert len(todos) == 2 * count
    assert all(todo["done"] for todo in todos if todo["text"] == "old")
