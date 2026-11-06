# todo-cli

A small Python command-line to-do app.

## Commands

- `todo add <text>` — add a new item
- `todo list` — list items
- `todo done <id>` — mark an item done
- `todo search <term>` — case-insensitive search (see `feat/search`)

## Storage

Todos are stored in a JSON file. Override the path with the `TODO_FILE` environment variable (default: `./todos.json`).

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
pytest
```
