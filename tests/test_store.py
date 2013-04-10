import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from study_planner.csvio import read_csv, write_csv
from study_planner.store import TaskStore
from study_planner.validation import PlannerError


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "nested" / "tasks.sqlite3"
        self.store = TaskStore(self.path)

    def tearDown(self):
        self.store.connection.close()
        self.directory.cleanup()

    def test_persistence_and_title_normalization(self):
        task = self.store.add("  Learn SQLite  ")
        self.assertEqual(task["title"], "Learn SQLite")
        self.assertTrue(task["created_at"].endswith("+00:00"))
        with TaskStore(self.path) as reopened:
            self.assertEqual(reopened.get(task["id"]), task)

    def test_validation_rejects_bad_titles_priorities_and_dates(self):
        for title in ("", "   ", "x" * 201, None):
            with self.subTest(title=title), self.assertRaises(PlannerError):
                self.store.add(title)
        with self.assertRaises(PlannerError):
            self.store.add("Example", priority="urgent")
        for value in ("2026-02-29", "20261104", "2026-W45-1", "tomorrow"):
            with self.subTest(date=value), self.assertRaises(PlannerError):
                self.store.add("Example", due_date=value)
        self.store.add("Leap year", due_date="2028-02-29")
        self.assertEqual(len(self.store.list_tasks()), 1)

    def test_priority_due_and_created_ordering(self):
        low = self.store.add("Low", priority="low")
        high = self.store.add("High", priority="high", due_date="2030-01-01")
        normal = self.store.add("Normal", due_date="2029-01-01")
        ids = lambda rows: [row["id"] for row in rows]
        self.assertEqual(ids(self.store.list_tasks()), [high["id"], normal["id"], low["id"]])
        self.assertEqual(ids(self.store.list_tasks(sort="due")), [normal["id"], high["id"], low["id"]])
        self.assertEqual(ids(self.store.list_tasks(sort="created")), [low["id"], high["id"], normal["id"]])
        with self.assertRaises(PlannerError):
            self.store.list_tasks(sort="id; DROP TABLE tasks")

    def test_completion_is_idempotent_and_reopening_clears_timestamp(self):
        task = self.store.add("Review notes")
        with patch("study_planner.store.now_iso", return_value="2030-01-01T12:00:00+00:00"):
            completed = self.store.set_status(task["id"], "done")
        with patch("study_planner.store.now_iso", return_value="2031-01-01T12:00:00+00:00"):
            self.assertEqual(self.store.set_status(task["id"], "done"), completed)
        self.assertEqual(self.store.list_tasks(), [])
        reopened = self.store.set_status(task["id"], "open")
        self.assertIsNone(reopened["completed_at"])

    def test_edits_are_validated_before_updating(self):
        task = self.store.add("Original", due_date="2030-01-01")
        with self.assertRaises(PlannerError):
            self.store.update(task["id"], title="Changed", due_date="invalid")
        self.assertEqual(self.store.get(task["id"])["title"], "Original")
        updated = self.store.update(task["id"], title="Revised", priority="high", clear_due=True)
        self.assertEqual((updated["title"], updated["priority"], updated["due_date"]), ("Revised", "high", None))
        with self.assertRaises(PlannerError):
            self.store.update(task["id"])

    def test_literal_search_preserves_sql_and_wildcard_characters(self):
        task = self.store.add("100%_SQL O'Reilly")
        self.store.add("Other")
        self.assertEqual(self.store.list_tasks(search="%_")[0]["id"], task["id"])
        self.assertEqual(len(self.store.list_tasks(search="sql")), 1)
        self.assertEqual(self.store.list_tasks(search="%' OR 1=1--"), [])
        self.assertEqual(self.store.summary()["total"], 2)

    def test_due_filters_and_summary_use_local_today(self):
        self.store.add("Old", priority="high", due_date="2030-01-01")
        self.store.add("Today", due_date="2030-01-02")
        self.store.add("Undated")
        done = self.store.add("Completed", due_date="2029-01-01")
        self.store.set_status(done["id"], "done")
        with patch("study_planner.store.today_iso", return_value="2030-01-02"):
            self.assertEqual([r["title"] for r in self.store.list_tasks(overdue=True)], ["Old"])
            self.assertEqual(len(self.store.list_tasks(status="all", due_before="2030-01-02")), 2)
            summary = self.store.summary()
        self.assertEqual((summary["total"], summary["open"], summary["done"], summary["overdue"]), (4, 3, 1, 1))
        self.assertEqual(summary["open_by_priority"], {"high": 1, "normal": 2, "low": 0})

    def test_csv_round_trip_preserves_task_fields(self):
        first = self.store.add('Read, "caf\u00e9"\npart two', priority="high", due_date="2030-01-01")
        self.store.set_status(first["id"], "done")
        self.store.add("Plain")
        output = io.StringIO(newline="")
        self.assertEqual(write_csv(self.store, output), 2)
        with TaskStore(":memory:") as other:
            self.assertEqual(read_csv(other, io.StringIO(output.getvalue())), 2)
            fields = ("title", "priority", "due_date", "status")
            actual = [tuple(row[f] for f in fields) for row in other.list_tasks(status="all", sort="created")]
            expected = [tuple(row[f] for f in fields) for row in self.store.list_tasks(status="all", sort="created")]
            self.assertEqual(actual, expected)

    def test_invalid_csv_import_does_not_insert_partial_rows(self):
        self.store.add("Existing")
        data = "title,priority,due_date,status\nValid,normal,,open\nInvalid,normal,2030-02-30,open\n"
        with self.assertRaisesRegex(PlannerError, "CSV row 3"):
            read_csv(self.store, io.StringIO(data))
        self.assertEqual(self.store.summary()["total"], 1)
        for data in ("", "title\nExample\n", "title,title,due_date,status\na,b,,open\n"):
            with self.assertRaises(PlannerError):
                read_csv(self.store, io.StringIO(data))

    def test_database_failure_rolls_back_entire_import(self):
        self.store.connection.execute("""
            CREATE TRIGGER reject_blocked BEFORE INSERT ON tasks
            WHEN NEW.title = 'blocked' BEGIN SELECT RAISE(ABORT, 'blocked'); END
        """)
        records = [{"title": title, "priority": "normal", "due_date": "", "status": "open"}
                   for title in ("allowed", "blocked")]
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.import_tasks(records)
        self.assertEqual(self.store.summary()["total"], 0)

    def test_delete_and_missing_ids(self):
        task = self.store.add("Disposable")
        self.assertEqual(self.store.delete(task["id"])["title"], "Disposable")
        with self.assertRaises(PlannerError):
            self.store.get(task["id"])

    def test_empty_summary(self):
        self.assertEqual(self.store.summary(), {"total": 0, "open": 0, "done": 0, "overdue": 0,
                                               "open_by_priority": {"high": 0, "normal": 0, "low": 0}})


if __name__ == "__main__":
    unittest.main()
