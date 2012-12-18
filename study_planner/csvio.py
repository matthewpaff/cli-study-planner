"""Portable CSV exchange for study tasks."""
import csv

FIELDS = ("title", "priority", "due_date", "status")


def write_csv(store, destination):
    writer = csv.DictWriter(destination, fieldnames=FIELDS)
    writer.writeheader()
    tasks = store.list_tasks(status="all", sort="created")
    for task in tasks:
        writer.writerow({field: task[field] for field in FIELDS})
    return len(tasks)
