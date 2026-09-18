import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from app.backend.http import make_server


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = make_server(0, Path(self.tmp.name) / 'cases.db')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]
        self.cookie = ''
        self.request('GET', '/')

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, method, path, payload=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port)
        base = {'Content-Type': 'application/json', 'Cookie': self.cookie,
                'Origin': f'http://127.0.0.1:{self.port}'}
        base.update(headers or {})
        connection.request(method, path, json.dumps(payload) if payload is not None else None, base)
        response = connection.getresponse()
        if response.getheader('Set-Cookie'):
            self.cookie = response.getheader('Set-Cookie').split(';')[0]
        data = response.read()
        status = response.status
        connection.close()
        return status, json.loads(data) if data.startswith(b'{') else data

    def create(self, text='50 EL-MCB-1P16 and 20 BX-IP65-2015-A'):
        status, case = self.request('POST', '/api/cases', {'text': text, 'title': 'Maintenance supplies', 'recipient': 'Purchasing team', 'customer_confirmed': True})
        self.assertEqual(status, 201)
        return case

    def test_happy_review_pdf_and_persistence(self):
        case = self.create()
        self.assertEqual(case['evaluation']['total'], '1866.63')
        status, reviewed = self.request('POST', f'/api/cases/{case["id"]}/review', {'revision': 1})
        self.assertEqual(status, 200)
        self.assertTrue(reviewed['reviewed'])
        status, pdf = self.request('GET', f'/api/cases/{case["id"]}/pdf')
        self.assertEqual(status, 200)
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertEqual(self.request('GET', '/api/cases')[1]['cases'][0]['id'], case['id'])

    def test_stale_write_and_review_invalidation(self):
        case = self.create()
        self.request('POST', f'/api/cases/{case["id"]}/review', {'revision': 1})
        lines = case['lines']
        lines[0]['qty'] = 60
        status, updated = self.request('PATCH', f'/api/cases/{case["id"]}', {'revision': 1, 'lines': lines})
        self.assertEqual(status, 200)
        self.assertFalse(updated['reviewed'])
        self.assertEqual(updated['revision'], 2)
        status, _ = self.request('PATCH', f'/api/cases/{case["id"]}', {'revision': 1, 'lines': lines})
        self.assertEqual(status, 409)

    def test_exception_cannot_be_reviewed(self):
        case = self.create('20 IP65 junction boxes 200 x 150 mm')
        status, _ = self.request('POST', f'/api/cases/{case["id"]}/review', {'revision': 1})
        self.assertEqual(status, 409)
        self.assertEqual(self.request('GET', f'/api/cases/{case["id"]}/pdf')[0], 409)

    def test_cross_origin_and_unauthenticated_rejected(self):
        self.assertEqual(self.request('POST', '/api/cases', {}, {'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request('GET', '/api/cases', headers={'Cookie': ''})[0], 401)

    def test_upload_and_oversized_text_rejected(self):
        self.assertEqual(self.request('POST', '/api/cases', {}, {'Content-Type': 'multipart/form-data'})[0], 415)
        self.assertEqual(self.request('POST', '/api/cases', {'text': 'x' * 20001})[0], 400)

    def test_currency_request_blocks(self):
        case = self.create('50 EL-MCB-1P16 in USD')
        self.assertTrue(case['evaluation']['blocks'])

    def test_frontend_assets_and_catalogue_specifications(self):
        for path in ('/', '/css/style.css', '/js/app.js', '/js/specifications.js'):
            self.assertEqual(self.request('GET', path)[0], 200, path)
        self.assertEqual(self.request('GET', '/database/schema.sql')[0], 404)
        status, catalogue = self.request('GET', '/api/catalogue')
        self.assertEqual(status, 200)
        self.assertEqual(catalogue['products'][0]['specifications']['current'], '16 A')

    def test_approval_cannot_be_forged(self):
        case = self.create('10 EL-MCB-1P16 with 20 percent discount')
        status, _ = self.request('PATCH', f'/api/cases/{case["id"]}', {'revision': 1, 'reviewed': True})
        self.assertEqual(status, 400)
        self.assertEqual(self.request('POST', f'/api/cases/{case["id"]}/review', {'revision': 1})[0], 409)

    def test_full_demo_approval_and_revision_snapshots(self):
        case = self.create('10 EL-MCB-1P16 with 20 percent discount')
        path = f'/api/cases/{case["id"]}'
        status, requested = self.request('POST', path + '/request-approvals', {'revision': 1})
        self.assertEqual(status, 200)
        self.assertEqual(requested['approvals'][0]['status'], 'pending')
        decision = {'revision': 1, 'decision': 'approved', 'reason': 'Synthetic demo exception'}
        self.assertEqual(self.request('POST', path + '/decision', decision)[0], 403)
        self.assertEqual(self.request('POST', path + '/decision', decision,
                                     {'X-Demo-Actor': 'manager'})[0], 403)
        status, approved = self.request('POST', path + '/decision', decision,
                                       {'X-Demo-Actor': 'finance'})
        self.assertEqual(status, 200)
        self.assertEqual(approved['status'], 'Ready for review')
        self.assertEqual(self.request('POST', path + '/review', {'revision': 1},
                                     {'X-Demo-Actor': 'finance'})[0], 403)
        self.assertEqual(self.request('POST', path + '/review', {'revision': 1})[0], 200)
        updated_lines = case['lines']
        updated_lines[0]['qty'] = 20
        status, revised = self.request('PATCH', path, {'revision': 1, 'lines': updated_lines})
        self.assertEqual(status, 200)
        self.assertFalse(revised['reviewed'])
        self.assertEqual(revised['status'], 'Awaiting approval')
        self.assertEqual(self.request('POST', path + '/decision', decision,
                                     {'X-Demo-Actor': 'finance'})[0], 409)
        status, history = self.request('GET', path + '/revisions')
        self.assertEqual(status, 200)
        self.assertEqual([r['lines'][0]['qty'] for r in history['revisions']], [10, 20])

    def test_approver_cannot_edit_or_create(self):
        case = self.create()
        headers = {'X-Demo-Actor': 'finance'}
        self.assertEqual(self.request('PATCH', f'/api/cases/{case["id"]}',
                                     {'revision': 1, 'recipient': 'Changed'}, headers)[0], 403)
        self.assertEqual(self.request('POST', '/api/cases', {}, headers)[0], 403)
        self.assertEqual(self.request('GET', '/api/cases', headers={'X-Demo-Actor': 'invented'})[0], 403)

    def test_approval_request_cannot_override_delivery_block(self):
        case = self.create('80 LT-PNL-36W-4K with another 20 percent discount')
        status, _ = self.request('POST', f'/api/cases/{case["id"]}/request-approvals', {'revision': 1})
        self.assertEqual(status, 409)
