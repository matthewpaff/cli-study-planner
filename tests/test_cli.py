import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = Path(self.directory.name) / "tasks.sqlite3"

    def tearDown(self):
        self.directory.cleanup()

    def run_cli(self, *args, input_text=None):
        return subprocess.run([sys.executable, "-m", "study_planner", "--db", str(self.db), *args],
                              cwd=ROOT, input=input_text, encoding="utf-8",
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)

    def test_help_and_version_do_not_create_a_database(self):
        help_result = self.run_cli("--help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("summary", help_result.stdout)
        version = self.run_cli("--version")
        self.assertEqual(version.returncode, 0)
        self.assertEqual(version.stdout.strip(), "0.1.0")
        self.assertFalse(self.db.exists())

    def test_add_show_complete_and_reopen(self):
        added = self.run_cli("add", "Review Python", "--priority", "high", "--due", "2030-01-01")
        self.assertEqual(added.returncode, 0, added.stderr)
        self.assertIn("Added task #1", added.stdout)
        task = json.loads(self.run_cli("show", "1", "--json").stdout)
        self.assertEqual((task["priority"], task["due_date"]), ("high", "2030-01-01"))
        self.assertEqual(self.run_cli("done", "1").returncode, 0)
        self.assertEqual(json.loads(self.run_cli("list", "--json").stdout), [])
        completed = json.loads(self.run_cli("list", "--status", "done", "--json").stdout)
        self.assertIsNotNone(completed[0]["completed_at"])
        self.assertEqual(self.run_cli("reopen", "1").returncode, 0)
        self.assertEqual(len(json.loads(self.run_cli("list", "--json").stdout)), 1)

    def test_unicode_and_control_characters_render_cleanly(self):
        title = "Study caf\u00e9 \u65e5\u672c\u8a9e\nnotes"
        added = self.run_cli("add", title)
        self.assertEqual(added.returncode, 0, added.stderr)
        result = self.run_cli("list")
        self.assertEqual(result.returncode, 0)
        self.assertIn("caf\u00e9 \u65e5\u672c\u8a9e\\nnotes", result.stdout)
        self.assertEqual(len(result.stdout.splitlines()), 2)
        tasks = json.loads(self.run_cli("list", "--json").stdout)
        self.assertEqual(tasks[0]["title"], title)

    def test_invalid_input_has_actionable_exit_codes(self):
        for args in (("add", "   "), ("add", "Bad date", "--due", "2030-02-30"),
                     ("show", "999"), ("show", "-1")):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("error:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_edit_clear_due_and_delete(self):
        self.run_cli("add", "Original", "--due", "2030-01-01")
        updated = self.run_cli("update", "1", "--title", "Revised", "--clear-due")
        self.assertEqual(updated.returncode, 0, updated.stderr)
        task = json.loads(self.run_cli("show", "1", "--json").stdout)
        self.assertEqual(task["title"], "Revised")
        self.assertIsNone(task["due_date"])
        self.assertEqual(self.run_cli("delete", "1").returncode, 0)
        self.assertEqual(self.run_cli("show", "1").returncode, 2)

    def test_csv_stdin_and_stdout_exchange(self):
        data = 'title,priority,due_date,status\n"Read, write",high,2030-01-01,done\n'
        imported = self.run_cli("import", "-", input_text=data)
        self.assertEqual(imported.returncode, 0, imported.stderr)
        exported = self.run_cli("export")
        self.assertEqual(exported.returncode, 0, exported.stderr)
        rows = list(csv.DictReader(io.StringIO(exported.stdout)))
        self.assertEqual(rows, [{"title": "Read, write", "priority": "high",
                                 "due_date": "2030-01-01", "status": "done"}])

    def test_bad_csv_is_atomic_and_does_not_print_a_traceback(self):
        data = "title,priority,due_date,status\nValid,normal,,open\nInvalid,normal,bad-date,open\n"
        result = self.run_cli("import", "-", input_text=data)
        self.assertEqual(result.returncode, 2)
        self.assertIn("CSV row 3", result.stderr)
        summary = json.loads(self.run_cli("summary", "--json").stdout)
        self.assertEqual(summary["total"], 0)

    def test_file_errors_return_one_without_a_traceback(self):
        result = self.run_cli("import", str(Path(self.directory.name) / "missing.csv"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
