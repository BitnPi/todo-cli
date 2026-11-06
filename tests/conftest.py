"""Shared fixtures. Every test runs in a temp cwd so no real todos.json is touched."""

import pytest


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TODO_FILE", raising=False)


@pytest.fixture
def todo_file(tmp_path, monkeypatch):
    path = tmp_path / "custom" / "my-todos.json"
    monkeypatch.setenv("TODO_FILE", str(path))
    return path
