"""Portable CSV exchange for study tasks."""
import csv

from .validation import PlannerError

FIELDS = ("title", "priority", "due_date", "status")


def write_csv(store, destination):
    writer = csv.DictWriter(destination, fieldnames=FIELDS)
    writer.writeheader()
    tasks = store.list_tasks(status="all", sort="created")
    for task in tasks:
        writer.writerow({field: task[field] for field in FIELDS})
    return len(tasks)


def read_csv(store, source):
    reader = csv.DictReader(source, strict=True)
    try:
        headers = reader.fieldnames
        if headers:
            headers[0] = headers[0].lstrip("\ufeff")
        if not headers or len(headers) != len(FIELDS) or set(headers) != set(FIELDS):
            raise PlannerError("CSV header must contain title, priority, due_date, status")
        records = []
        for number, record in enumerate(reader, start=2):
            if None in record or any(value is None for value in record.values()):
                raise PlannerError("CSV row {} has the wrong number of columns".format(number))
            records.append(record)
    except csv.Error as error:
        raise PlannerError("Invalid CSV: {}".format(error))
    return store.import_tasks(records)
