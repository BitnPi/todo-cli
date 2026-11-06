"""CLI entrypoint."""

import argparse
import sys

from todo import storage


def cmd_add(args: argparse.Namespace) -> int:
    text = " ".join(args.text).strip()
    if not text:
        print("todo: text must not be empty", file=sys.stderr)
        return 1
    path = storage.todo_path()
    with storage.locked(path):
        todos = storage.load(path)
        new_id = storage.next_id(todos)
        todos.append({"id": new_id, "text": text, "done": False})
        storage.save(path, todos)
    print(new_id)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    for todo in storage.load(storage.todo_path()):
        mark = "x" if todo["done"] else " "
        print(f"{todo['id']}: [{mark}] {todo['text']}")
    return 0


def cmd_done(args: argparse.Namespace) -> int:
    path = storage.todo_path()
    with storage.locked(path):
        todos = storage.load(path)
        for todo in todos:
            if todo["id"] == args.id:
                todo["done"] = True
                storage.save(path, todos)
                return 0
    print(f"todo: no item with id {args.id}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="todo", description="A small to-do app.")
    commands = parser.add_subparsers(dest="command", metavar="<command>")

    add = commands.add_parser("add", help="add a new item and print its id")
    add.add_argument("text", nargs="+", help="item text")
    add.set_defaults(func=cmd_add)

    list_ = commands.add_parser("list", help="list all items")
    list_.set_defaults(func=cmd_list)

    done = commands.add_parser("done", help="mark an item done")
    done.add_argument("id", type=int, help="item id")
    done.set_defaults(func=cmd_done)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except (storage.StorageError, OSError) as exc:
        print(f"todo: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
