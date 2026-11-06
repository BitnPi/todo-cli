"""Tests for JSON persistence."""

import json

import pytest

from todo import storage


def test_todo_path_default():
    assert str(storage.todo_path()) == "todos.json"


def test_todo_path_reads_env_at_call_time(monkeypatch, tmp_path):
    monkeypatch.setenv("TODO_FILE", str(tmp_path / "x.json"))
    assert storage.todo_path() == tmp_path / "x.json"


def test_load_missing_file_returns_empty(tmp_path):
    assert storage.load(tmp_path / "none.json") == []


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "t.json"
    todos = [{"id": 1, "text": "a", "done": True}]
    storage.save(path, todos)
    assert storage.load(path) == todos


def test_save_creates_parent_dirs_and_leaves_no_temp_file(tmp_path):
    path = tmp_path / "a" / "b" / "t.json"
    storage.save(path, [])
    assert [p.name for p in path.parent.iterdir()] == ["t.json"]


def test_failed_save_keeps_existing_data(tmp_path, monkeypatch):
    path = tmp_path / "t.json"
    todos = [{"id": 1, "text": "a", "done": False}]
    storage.save(path, todos)

    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr(storage.os, "replace", fail)
    with pytest.raises(OSError):
        storage.save(path, [])
    assert storage.load(path) == todos
    assert [p.name for p in tmp_path.iterdir()] == ["t.json"]


@pytest.mark.parametrize(
    "data",
    [
        {"id": 1},
        ["x"],
        [{"id": 1, "text": "a"}],
        [{"id": "1", "text": "a", "done": False}],
        [{"id": True, "text": "a", "done": False}],
        [{"id": 1, "text": 2, "done": False}],
        [{"id": 1, "text": "a", "done": 0}],
    ],
)
def test_load_rejects_wrong_schema(tmp_path, data):
    path = tmp_path / "t.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(storage.StorageError):
        storage.load(path)


def test_load_rejects_invalid_utf8(tmp_path):
    path = tmp_path / "t.json"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(storage.StorageError):
        storage.load(path)


@pytest.mark.parametrize(
    ("ids", "expected"), [([], 1), ([1], 2), ([5, 2], 6), ([1, 3], 4)]
)
def test_next_id(ids, expected):
    todos = [{"id": i, "text": "t", "done": False} for i in ids]
    assert storage.next_id(todos) == expected
