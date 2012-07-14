# CLI Study Planner

A small, original Python/SQLite tool for managing study tasks from the terminal.
It uses **only Python's standard library**. No package installation or virtual
environment is needed. Requires Python 3.10 or newer with SQLite support.

## Quick start

Run these commands from the repository directory:

```console
python -m study_planner --help
python -m study_planner add "Review Python generators" --priority high --due 2026-12-01
python -m study_planner list
python -m study_planner show 1
python -m study_planner done 1
python -m study_planner summary
python -m study_planner focus --limit 3
```

Replace `1` with the ID printed by `add`. Tasks persist between commands in
`~/.study-planner/tasks.sqlite3`; the parent directory is created automatically.
`--help` and `--version` do not create a database.

To use a separate database, put the global `--db` argument **before** the command:

```console
python -m study_planner --db demo.sqlite3 import examples/tasks.csv
python -m study_planner --db demo.sqlite3 list --status all
```

## Find and organize tasks

`focus` shows three open tasks by default, highest priority first and then creation
order. Use `--limit 1` through `--limit 20` to choose the shortlist size, or `--json`
to consume it in a script. Completed tasks are excluded; the command changes no tasks.

```console
python -m study_planner list --sort due
python -m study_planner list --status done
python -m study_planner list --status all --search sqlite
python -m study_planner list --overdue
python -m study_planner list --due-before 2026-12-01
```

- `list` shows open tasks by default. Use `--status all` to include completed tasks.
- Priorities are `high`, `normal` (default), and `low`. The default sort puts high
  priority first, then orders equal-priority tasks by ID. `--sort created` uses
  creation order; `--sort due` places undated tasks last.
- Search is a literal substring search, case-insensitive for ASCII letters.
  SQL characters, `%`, and `_` are treated as text.
- Dates must be valid `YYYY-MM-DD` values. `--due-before` is strictly exclusive.
- An overdue task is open and due before today's local calendar date. Tasks due
  today are not overdue. Creation and completion timestamps are stored in UTC.

## Edit, complete, reopen, or delete

```console
python -m study_planner update 1 --title "Review iterators and generators" --priority normal
python -m study_planner update 1 --due 2026-12-15
python -m study_planner update 1 --clear-due
python -m study_planner done 1
python -m study_planner reopen 1
python -m study_planner delete 1
```

Titles are trimmed and must contain 1-200 characters. Repeating `done` preserves
the original completion timestamp; reopening clears it. `delete` permanently
removes the specified task.

## CSV exchange

```console
python -m study_planner export tasks.csv
python -m study_planner --db other.sqlite3 import tasks.csv
python -m study_planner export
```

CSV contains `title,priority,due_date,status`, with an empty due date for undated
tasks. Export includes both open and completed tasks. Files use UTF-8; quoted
commas, quotes, and newlines are supported. UTF-8 BOM input is accepted.

Import validates the entire file and inserts it in one transaction. Invalid
rows or database failures leave existing tasks unchanged. Imported rows are
**new tasks with new IDs and timestamps**; importing the same file again creates
another set of tasks. All four header names are required, in any order.

`export` without a path writes only CSV to stdout. `import -` reads stdin.

## Script-friendly output

```console
python -m study_planner list --status all --json
python -m study_planner show 1 --json
python -m study_planner summary --json
```

List output is a JSON array, show output is an object, and summary output includes
total/open/completed/overdue counts and open-task counts by priority.

Exit codes: `0` for success, `1` for file/database/encoding failures, and `2` for
invalid input. Errors are written to stderr without a traceback.

## Development

```console
python -m unittest discover -s tests -v
```

The standard-library suite covers persistence, validation, ordering, literal
search, date filtering, completion, CSV round trips, transaction rollback, Unicode
output, and command-line error handling. Tests use temporary databases.

See [CONTRIBUTING.md](CONTRIBUTING.md). Licensed under the [MIT license](LICENSE).

[History and provenance](HISTORY.md).
