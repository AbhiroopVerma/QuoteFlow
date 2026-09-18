"""Persistence boundary. No HTTP, pricing, or browser concerns live here."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[1] / 'data/cases.db'
SCHEMA_PATH = Path(__file__).with_name('schema.sql')


@contextmanager
def transaction(path, write=False):
    connection = sqlite3.connect(path)
    try:
        if write:
            connection.execute('BEGIN IMMEDIATE')
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize(path=DEFAULT_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with transaction(path) as connection:
        connection.executescript(SCHEMA_PATH.read_text())
        # Backfill only the current revision; prior lost inputs cannot be recreated.
        for case in list_cases(connection):
            exists = connection.execute('SELECT 1 FROM revisions WHERE case_id=? AND revision=?',
                                        (case['id'], case['revision'])).fetchone()
            if not exists:
                save_snapshot(connection, case)
    return path


def list_cases(connection):
    return [json.loads(row[0]) for row in connection.execute('SELECT data FROM cases ORDER BY rowid DESC')]


def get_case(connection, case_id):
    row = connection.execute('SELECT data FROM cases WHERE id=?', (case_id,)).fetchone()
    return json.loads(row[0]) if row else None


def create_case(connection, case):
    connection.execute('INSERT INTO cases (id,data) VALUES (?,?)', (case['id'], json.dumps(case)))


def update_case(connection, case):
    connection.execute('UPDATE cases SET data=? WHERE id=?', (json.dumps(case), case['id']))


def delete_case(connection, case_id):
    connection.execute('DELETE FROM revisions WHERE case_id=?', (case_id,))
    connection.execute('DELETE FROM cases WHERE id=?', (case_id,))


def save_snapshot(connection, case):
    fields = {key: case[key] for key in ('id', 'revision', 'title', 'text', 'recipient', 'lines', 'delivery_accepted')}
    fields['saved_at'] = datetime.now(timezone.utc).isoformat()
    connection.execute('INSERT INTO revisions (case_id,revision,data) VALUES (?,?,?)',
                       (case['id'], case['revision'], json.dumps(fields)))


def list_revisions(connection, case_id):
    rows = connection.execute('SELECT data FROM revisions WHERE case_id=? ORDER BY revision', (case_id,))
    return [json.loads(row[0]) for row in rows]
