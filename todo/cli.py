"""CLI entrypoint — scaffold only; features land on feat/core and feat/search."""

import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print("Usage: todo <add|list|done|search> ...")
        return 0
    print(f"todo: command '{args[0]}' not implemented yet", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
