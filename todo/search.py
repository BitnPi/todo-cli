"""Case-insensitive substring matching for `todo search`."""

from todo.storage import Todo


def search_todos(todos: list[Todo], term: str) -> list[Todo]:
    needle = term.casefold()
    return [todo for todo in todos if needle in todo["text"].casefold()]
