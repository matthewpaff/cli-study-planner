"""Command-line entry point."""
import argparse
from pathlib import Path
import sqlite3
import sys

from . import __version__
from .store import TaskStore


def build_parser():
    parser = argparse.ArgumentParser(description="Plan and track study tasks.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--db", default=str(Path.home() / ".study-planner" / "tasks.sqlite3"),
                        help="SQLite database path (default: ~/.study-planner/tasks.sqlite3)")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="Add a study task")
    add.add_argument("title")
    commands.add_parser("list", help="List tasks")
    return parser


def print_tasks(tasks):
    if not tasks:
        print("No tasks found.")
        return
    print("ID   STATUS PRIORITY DUE         TITLE")
    for task in tasks:
        title = task["title"].replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        print("{:<4} {:<6} {:<8} {:<11} {}".format(
            task["id"], task["status"], task["priority"], task["due_date"] or "-", title))


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        with TaskStore(args.db) as store:
            if args.command == "add":
                task = store.add(args.title)
                print("Added task #{}: {}".format(task["id"], task["title"]))
            elif args.command == "list":
                print_tasks(store.list_tasks())
        return 0
    except (OSError, sqlite3.Error) as error:
        print("error: {}".format(error), file=sys.stderr)
        return 1
