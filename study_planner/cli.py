"""Command-line entry point."""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import sqlite3
import sys

from . import __version__
from .csvio import read_csv, write_csv
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


def focus_limit(value):
    number = positive_id(value)
    if number > 20:
        raise argparse.ArgumentTypeError("Focus limit must be between 1 and 20")
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
    listing.add_argument("--search", help="Find a literal substring (ASCII case-insensitive)")
    listing.add_argument("--status", choices=("open", "done", "all"), default="open")
    listing.add_argument("--due-before", help="Due strictly before YYYY-MM-DD")
    listing.add_argument("--overdue", action="store_true", help="Only open tasks due before today")
    listing.add_argument("--json", action="store_true", help="Write JSON for scripts")
    focus = commands.add_parser("focus", help="Show a short list of open tasks in priority order")
    focus.add_argument("--limit", type=focus_limit, default=3, help="Number of tasks, 1-20 (default: 3)")
    focus.add_argument("--json", action="store_true")
    show = commands.add_parser("show", help="Show one task")
    show.add_argument("id", type=positive_id)
    show.add_argument("--json", action="store_true")
    for name, help_text in (("done", "Complete a task"), ("reopen", "Reopen a completed task"),
                            ("delete", "Permanently delete one task")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("id", type=positive_id)
    update = commands.add_parser("update", help="Edit task details")
    update.add_argument("id", type=positive_id)
    update.add_argument("--title")
    update.add_argument("--priority", choices=PRIORITIES)
    due = update.add_mutually_exclusive_group()
    due.add_argument("--due")
    due.add_argument("--clear-due", action="store_true")
    summary = commands.add_parser("summary", help="Summarize task progress")
    summary.add_argument("--json", action="store_true")
    export = commands.add_parser("export", help="Export all tasks to CSV")
    export.add_argument("path", nargs="?", default="-", help="Output file, or - for stdout")
    importing = commands.add_parser("import", help="Import CSV rows as new tasks")
    importing.add_argument("path", help="Input file, or - for stdin")
    return parser


def print_json(value):
    print(json.dumps(value, ensure_ascii=True, indent=2))


def print_tasks(tasks, as_json=False):
    if as_json:
        print_json(tasks)
        return
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
                print_tasks(store.list_tasks(sort=args.sort, search=args.search, status=args.status,
                                             due_before=args.due_before, overdue=args.overdue), as_json=args.json)
            elif args.command == "focus":
                print_tasks(store.list_tasks(status="open", sort="priority")[:args.limit], as_json=args.json)
            elif args.command == "show":
                task = store.get(args.id)
                if args.json:
                    print_json(task)
                else:
                    print_tasks([task])
            elif args.command in ("done", "reopen"):
                task = store.set_status(args.id, "done" if args.command == "done" else "open")
                print("Task #{} marked {}.".format(task["id"], task["status"]))
            elif args.command == "update":
                print_tasks([store.update(args.id, title=args.title, priority=args.priority,
                                         due_date=args.due, clear_due=args.clear_due)])
            elif args.command == "summary":
                counts = store.summary()
                if args.json:
                    print_json(counts)
                else:
                    for key in ("total", "open", "done", "overdue"):
                        print("{}: {}".format(key.capitalize(), counts[key]))
                    print("Open by priority: " + ", ".join(
                        "{}={}".format(key, value) for key, value in counts["open_by_priority"].items()))
            elif args.command == "export":
                target = nullcontext(sys.stdout) if args.path == "-" else open(
                    args.path, "w", encoding="utf-8", newline="")
                with target as handle:
                    count = write_csv(store, handle)
                if args.path != "-":
                    print("Exported {} tasks.".format(count))
            elif args.command == "import":
                source = nullcontext(sys.stdin) if args.path == "-" else open(
                    args.path, "r", encoding="utf-8-sig", newline="")
                with source as handle:
                    count = read_csv(store, handle)
                print("Imported {} tasks.".format(count))
            elif args.command == "delete":
                task = store.delete(args.id)
                print("Deleted task #{}.".format(task["id"]))
        return 0
    except PlannerError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 2
    except (OSError, sqlite3.Error, UnicodeError) as error:
        print("error: {}".format(error), file=sys.stderr)
        return 1
