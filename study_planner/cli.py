"""Command-line entry point."""
import argparse
from pathlib import Path
import sqlite3
import sys

from . import __version__
from .store import TaskStore
from .validation import PlannerError, PRIORITIES


def positive_id(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Task ID must be a positive integer")
    if number < 1:
        raise argparse.ArgumentTypeError("Task ID must be a positive integer")
    return number


def build_parser():
    parser = argparse.ArgumentParser(description="Plan and track study tasks.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--db", default=str(Path.home() / ".study-planner" / "tasks.sqlite3"),
                        help="SQLite database path (default: ~/.study-planner/tasks.sqlite3)")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="Add a study task")
    add.add_argument("title")
    add.add_argument("--priority", choices=PRIORITIES, default="normal")
    add.add_argument("--due", help="Due date in YYYY-MM-DD format")
    listing = commands.add_parser("list", help="List tasks")
    listing.add_argument("--sort", choices=("priority", "created", "due"), default="priority")
    show = commands.add_parser("show", help="Show one task")
    show.add_argument("id", type=positive_id)
    for name, help_text in (("done", "Complete a task"), ("reopen", "Reopen a completed task")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("id", type=positive_id)
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
                task = store.add(args.title, priority=args.priority, due_date=args.due)
                print("Added task #{}: {}".format(task["id"], task["title"]))
            elif args.command == "list":
                print_tasks(store.list_tasks(sort=args.sort))
            elif args.command == "show":
                print_tasks([store.get(args.id)])
            elif args.command in ("done", "reopen"):
                task = store.set_status(args.id, "done" if args.command == "done" else "open")
                print("Task #{} marked {}.".format(task["id"], task["status"]))
        return 0
    except PlannerError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 2
    except (OSError, sqlite3.Error) as error:
        print("error: {}".format(error), file=sys.stderr)
        return 1
