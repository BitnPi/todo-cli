"""Tests for JSON persistence."""

import json
import os
import stat
import threading
from pathlib import Path

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


def test_save_leaves_unrelated_tmp_file_alone(tmp_path, monkeypatch):
    path = tmp_path / "t.json"
    other = tmp_path / "t.json.tmp"
    other.write_text("not ours", encoding="utf-8")

    storage.save(path, [])
    assert other.read_text(encoding="utf-8") == "not ours"

    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr(storage.os, "replace", fail)
    with pytest.raises(OSError):
        storage.save(path, [])
    assert other.read_text(encoding="utf-8") == "not ours"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["t.json", "t.json.tmp"]


def test_each_save_uses_its_own_temp_file(tmp_path, monkeypatch):
    path = tmp_path / "t.json"
    sources = []
    real_replace = os.replace

    def spy(src, dst):
        sources.append(Path(src))
        real_replace(src, dst)

    monkeypatch.setattr(storage.os, "replace", spy)
    storage.save(path, [])
    storage.save(path, [])
    assert len(set(sources)) == 2
    assert all(src.parent == tmp_path for src in sources)


def test_concurrent_saves_never_expose_partial_json(tmp_path):
    path = tmp_path / "t.json"
    todos = [{"id": i, "text": "x" * 1000, "done": False} for i in range(1, 200)]
    storage.save(path, todos)
    stop = threading.Event()

    def writer():
        while not stop.is_set():
            storage.save(path, todos)

    threads = [threading.Thread(target=writer) for _ in range(4)]
    for thread in threads:
        thread.start()
    try:
        for _ in range(200):
            assert storage.load(path) == todos
    finally:
        stop.set()
        for thread in threads:
            thread.join()
    assert [p.name for p in tmp_path.iterdir()] == ["t.json"]


def test_save_preserves_existing_file_mode(tmp_path):
    path = tmp_path / "t.json"
    path.write_text("[]", encoding="utf-8")
    path.chmod(0o640)
    storage.save(path, [])
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


def test_save_new_file_follows_umask(tmp_path):
    path = tmp_path / "t.json"
    previous = os.umask(0o027)
    try:
        storage.save(path, [])
    finally:
        os.umask(previous)
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


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
