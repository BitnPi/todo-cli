# todo-cli

A small Python command-line to-do app.

## Commands

- `todo add <text>` — add a new item and print its id
- `todo list` — list all items as `id: [ ] text`, or `id: [x] text` for done items
- `todo done <id>` — mark an item done; exits non-zero if the id does not exist
- `todo search <term>` — case-insensitive search (see `feat/search`)

Example:

```console
$ todo add "buy milk"
1
$ todo add call the bank
2
$ todo done 1
$ todo list
1: [x] buy milk
2: [ ] call the bank
$ todo done 99
todo: no item with id 99
```

## Storage

Todos are stored in a JSON file. Override the path with the `TODO_FILE` environment variable (default: `./todos.json`).

The file holds a list of objects with an integer `id`, string `text` and boolean `done`. New ids are the highest existing id plus one.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
pytest
```
