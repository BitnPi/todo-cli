# todo-cli

A small Python command-line to-do app.

## Commands

- `todo add <text>` — add a new item and print its id
- `todo list` — list all items as `id: [ ] text`, or `id: [x] text` for done items
- `todo done <id>` — mark an item done; exits non-zero if the id does not exist
- `todo search <term>` — list items whose text contains `<term>`, ignoring case

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

### Search

```console
$ todo search MILK
1: [ ] Buy milk
3: [x] Milk the cow
```

Results use the same format as `todo list`. A search with no matches prints nothing and exits 0; omitting the term prints usage to stderr and exits non-zero. Unquoted multi-word terms are joined with spaces, so `todo search buy milk` looks for `buy milk`. Put `--` before a term that starts with a dash: `todo search -- -urgent`.

## Storage

Todos are stored in a JSON file. Override the path with the `TODO_FILE` environment variable (default: `./todos.json`).

The file holds a list of objects with an integer `id`, string `text` and boolean `done`. New ids are the highest existing id plus one.

`add` and `done` hold an exclusive lock on a sibling `<file>.lock` while they update the file, so concurrent commands don't lose each other's changes. The lock file stays in place and is safe to ignore. Locking uses `fcntl`, so it isn't available on Windows.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
pytest
```
