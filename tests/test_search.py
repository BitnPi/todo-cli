"""Tests for `todo search`; todos are seeded as JSON so no other command is needed."""

import json

import pytest

from todo.cli import main

TODOS = [
    {"id": 1, "text": "Buy milk", "done": False},
    {"id": 2, "text": "Call the bank", "done": False},
    {"id": 3, "text": "MILK the cow", "done": True},
]


@pytest.fixture
def todo_file(tmp_path, monkeypatch):
    path = tmp_path / "custom.json"
    path.write_text(json.dumps(TODOS), encoding="utf-8")
    monkeypatch.setenv("TODO_FILE", str(path))
    return path


@pytest.mark.parametrize("term", ["milk", "MILK", "mIlK"])
def test_search_is_case_insensitive(todo_file, capsys, term):
    assert main(["search", term]) == 0
    assert capsys.readouterr().out == "1: [ ] Buy milk\n3: [x] MILK the cow\n"


def test_search_matches_substring_within_word(todo_file, capsys):
    assert main(["search", "ank"]) == 0
    assert capsys.readouterr().out == "2: [ ] Call the bank\n"


def test_search_joins_multiple_words_into_one_term(todo_file, capsys):
    assert main(["search", "buy", "milk"]) == 0
    assert capsys.readouterr().out == "1: [ ] Buy milk\n"


def test_search_no_matches_prints_nothing_and_exits_zero(todo_file, capsys):
    assert main(["search", "nonexistent"]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.parametrize("args", [["search"], ["search", ""]])
def test_search_missing_term_prints_usage_to_stderr(todo_file, capsys, args):
    assert main(args) != 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Usage: todo search <term>" in captured.err


def test_search_reads_path_from_todo_file_not_cwd(todo_file, tmp_path, monkeypatch, capsys):
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    (cwd / "todos.json").write_text(
        json.dumps([{"id": 9, "text": "decoy milk", "done": False}]), encoding="utf-8"
    )
    monkeypatch.chdir(cwd)

    assert main(["search", "milk"]) == 0
    assert capsys.readouterr().out == "1: [ ] Buy milk\n3: [x] MILK the cow\n"


def test_search_defaults_to_todos_json_in_cwd(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("TODO_FILE", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "todos.json").write_text(json.dumps(TODOS), encoding="utf-8")

    assert main(["search", "bank"]) == 0
    assert capsys.readouterr().out == "2: [ ] Call the bank\n"


def test_search_missing_file_is_empty(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TODO_FILE", str(tmp_path / "absent.json"))

    assert main(["search", "milk"]) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("content", ["{not json", '{"id": 1}', '[{"id": 1}]', "[1]"])
def test_search_invalid_file_reports_error(tmp_path, monkeypatch, capsys, content):
    path = tmp_path / "bad.json"
    path.write_text(content, encoding="utf-8")
    monkeypatch.setenv("TODO_FILE", str(path))

    assert main(["search", "milk"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "cannot read todo file" in captured.err
