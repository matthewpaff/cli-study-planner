"""SQLite persistence for study tasks."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
        return dict(row) if row else None

    def add(self, title):
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO tasks (title, created_at) VALUES (?, ?)", (title, now_iso()))
        return self.get(cursor.lastrowid)

    def list_tasks(self):
        return [dict(row) for row in self.connection.execute("SELECT * FROM tasks ORDER BY id")]
