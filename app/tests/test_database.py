import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.database import repository as store


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'cases.db'
        store.initialize(self.path)
        self.case = {'id': 'Q-ABC123', 'revision': 1, 'title': 'Demo', 'text': '10 MCB',
                     'recipient': 'Buyer', 'lines': [{'sku': 'EL-MCB-1P16', 'qty': 10}],
                     'delivery_accepted': False}

    def tearDown(self):
        self.temp.cleanup()

    def test_case_and_snapshot_survive_reinitialization(self):
        with store.transaction(self.path, write=True) as db:
            store.create_case(db, self.case)
            store.save_snapshot(db, self.case)
        store.initialize(self.path)
        with store.transaction(self.path) as db:
            self.assertEqual(store.get_case(db, self.case['id']), self.case)
            self.assertEqual(len(store.list_revisions(db, self.case['id'])), 1)

    def test_failed_transaction_rolls_back_case_and_snapshot(self):
        with self.assertRaises(RuntimeError):
            with store.transaction(self.path, write=True) as db:
                store.create_case(db, self.case)
                store.save_snapshot(db, self.case)
                raise RuntimeError('Simulated failure')
        with store.transaction(self.path) as db:
            self.assertIsNone(store.get_case(db, self.case['id']))
            self.assertEqual(store.list_revisions(db, self.case['id']), [])

    def test_snapshots_cannot_be_overwritten(self):
        with store.transaction(self.path, write=True) as db:
            store.create_case(db, self.case)
            store.save_snapshot(db, self.case)
        self.case['lines'][0]['qty'] = 20
        with self.assertRaises(sqlite3.IntegrityError):
            with store.transaction(self.path, write=True) as db:
                store.save_snapshot(db, self.case)
        with store.transaction(self.path) as db:
            self.assertEqual(store.list_revisions(db, self.case['id'])[0]['lines'][0]['qty'], 10)

    def test_delete_case_removes_revision_inputs(self):
        with store.transaction(self.path, write=True) as db:
            store.create_case(db, self.case)
            store.save_snapshot(db, self.case)
            store.delete_case(db, self.case['id'])
        with store.transaction(self.path) as db:
            self.assertEqual(store.list_cases(db), [])
            self.assertEqual(store.list_revisions(db, self.case['id']), [])
