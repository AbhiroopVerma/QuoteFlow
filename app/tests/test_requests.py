"""Run the HTTP request dispatcher in memory, with no listening sockets."""

import io
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.backend.http import Handler, make_server
from app.tests import test_server


class InProcessRequestTests(test_server.ServerTests):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.port = 8765
        with patch('app.backend.http.ThreadingHTTPServer', return_value=SimpleNamespace(server_port=self.port)):
            self.server = make_server(self.port, Path(self.tmp.name) / 'cases.db')
        self.cookie = ''
        self.request('GET', '/')

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, method, path, payload=None, headers=None):
        body = json.dumps(payload).encode() if payload is not None else b''
        request = object.__new__(Handler)
        request.server = self.server
        request.command, request.path = method, path
        request.rfile = io.BytesIO(body)
        request.headers = {'Host': f'127.0.0.1:{self.port}',
                           'Content-Type': 'application/json', 'Cookie': self.cookie,
                           'Content-Length': str(len(body)),
                           'Origin': f'http://127.0.0.1:{self.port}', **(headers or {})}
        result = []

        def capture(status, data, content_type='application/json', cookie=False, filename=None):
            if cookie:
                self.cookie = f'qf_session={self.server.token}'
            result.extend([status, data])

        request.respond = capture
        request.handle_request()
        return tuple(result)
