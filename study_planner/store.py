"""SQLite persistence for study tasks."""
from datetime import date, datetime, timezone
from pathlib import Path
import sqlite3

from .validation import PlannerError, validate_due, validate_priority, validate_status, validate_title


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today_iso():
    return date.today().isoformat()


class TaskStore:
    def __init__(self, path):
        path = str(path)
        if path != ":memory:":
            path = str(Path(path).expanduser())
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        with self.connection:
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 200),
                    priority TEXT NOT NULL DEFAULT 'normal'
                        CHECK(priority IN ('low', 'normal', 'high')),
                    due_date TEXT,
                    status TEXT NOT NULL DEFAULT 'open'
                        CHECK(status IN ('open', 'done')),
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.connection.close()

    def get(self, task_id):
        row = self.connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise PlannerError("Task #{} does not exist".format(task_id))
        return dict(row)

    def add(self, title, priority="normal", due_date=None):
        title = validate_title(title)
        priority = validate_priority(priority)
        due_date = validate_due(due_date)
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO tasks (title, priority, due_date, created_at) VALUES (?, ?, ?, ?)",
                (title, priority, due_date, now_iso()))
        return self.get(cursor.lastrowid)

    def list_tasks(self, sort="priority", search=None, status="open", due_before=None, overdue=False):
        orders = {"priority": "CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, id",
                  "created": "id", "due": "due_date IS NULL, due_date, id"}
        if sort not in orders:
            raise PlannerError("Unknown sort order")
        sql = "SELECT * FROM tasks"
        clauses, values = [], []
        if status != "all":
            clauses.append("status = ?")
            values.append(validate_status(status))
        if due_before is not None:
            clauses.append("due_date < ?")
            values.append(validate_due(due_before))
        if overdue:
            clauses.extend(["status = 'open'", "due_date < ?"])
            values.append(today_iso())
        if search:
            clauses.append("instr(lower(title), lower(?)) > 0")
            values.append(search)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY " + orders[sort]
        return [dict(row) for row in self.connection.execute(sql, values)]

    def set_status(self, task_id, status):
        status = validate_status(status)
        task = self.get(task_id)
        if task["status"] == status:
            return task
        with self.connection:
            self.connection.execute(
                "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?",
                (status, now_iso() if status == "done" else None, task_id))
        return self.get(task_id)

    def update(self, task_id, title=None, priority=None, due_date=None, clear_due=False):
        task = self.get(task_id)
        if clear_due and due_date is not None:
            raise PlannerError("Choose either a due date or clear_due")
        if title is None and priority is None and due_date is None and not clear_due:
            raise PlannerError("Provide at least one task change")
        new_title = validate_title(title) if title is not None else task["title"]
        new_priority = validate_priority(priority) if priority is not None else task["priority"]
        new_due = validate_due(due_date) if due_date is not None else task["due_date"]
        if clear_due:
            new_due = None
        with self.connection:
            self.connection.execute(
                "UPDATE tasks SET title = ?, priority = ?, due_date = ? WHERE id = ?",
                (new_title, new_priority, new_due, task_id))
        return self.get(task_id)

    def summary(self):
        counts = dict(self.connection.execute("""
            SELECT COUNT(*) AS total,
                   COALESCE(SUM(status = 'open'), 0) AS open,
                   COALESCE(SUM(status = 'done'), 0) AS done,
                   COALESCE(SUM(status = 'open' AND due_date < ?), 0) AS overdue
            FROM tasks
        """, (today_iso(),)).fetchone())
        priorities = {"high": 0, "normal": 0, "low": 0}
        for row in self.connection.execute(
                "SELECT priority, COUNT(*) AS count FROM tasks WHERE status = 'open' GROUP BY priority"):
            priorities[row["priority"]] = row["count"]
        counts["open_by_priority"] = priorities
        return counts
