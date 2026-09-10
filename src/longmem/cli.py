import argparse
import json

from .config import load_config, make_store


def main():
    parser = argparse.ArgumentParser(description="Persistent memory CLI")
    parser.add_argument("--config", help="YAML config; otherwise LONGMEM_CONFIG or configs/local.yaml")
    commands = parser.add_subparsers(dest="command", required=True)
    write = commands.add_parser("write")
    write.add_argument("content")
    write.add_argument("--id", dest="memory_id")
    write.add_argument("--supersedes")
    write.add_argument("--source", default="user")
    write.add_argument("--importance", type=float, default=0.5)
    get = commands.add_parser("get")
    get.add_argument("memory_id")
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--top-k", type=int, default=5)
    listing = commands.add_parser("list")
    listing.add_argument("--include-superseded", action="store_true")
    commands.add_parser("rebuild-index")
    args = vars(parser.parse_args())
    store = make_store(load_config(args.pop("config")))
    command = args.pop("command")
    if command == "write":
        result = store.write(**args).to_dict()
    elif command == "get":
        memory = store.get(**args)
        result = memory.to_dict() if memory else None
    elif command == "list":
        result = [memory.to_dict() for memory in store.list(**args)]
    elif command == "search":
        result = store.search(**args)
    else:
        result = store.rebuild_index()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
