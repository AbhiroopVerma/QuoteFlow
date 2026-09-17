"""Single-user localhost sandbox; never bind this demo to a public interface."""

import argparse
import json
import mimetypes
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from app.domain import CATALOGUE, evaluate, extract, public_quote, quote_hash
from app.documents import email_draft, render_pdf

ROOT = Path(__file__).resolve().parent


class RequestError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def enrich(case):
    case['evaluation'] = evaluate(case['lines'], delivery_accepted=case['delivery_accepted'])
    if re.search(r'\b(USD|EUR|GBP|MYR|AUD)\b', case['text'], re.I):
        case['evaluation']['blocks'].append('Only SGD is in scope. Correct the source enquiry to continue.')
        case['evaluation']['status'] = 'Needs clarification'
    case['status'] = 'Reviewed' if case['reviewed'] else case['evaluation']['status']
    case['quote'] = public_quote(case)
    case['document_hash'] = quote_hash(case)
    case['email'] = email_draft(case['quote'])
    return case


class Handler(BaseHTTPRequestHandler):
    server_version = 'QuoteFlow/0.1'

    def log_message(self, *_):
        pass  # No request bodies, source text, URLs or financial data in logs.

    def respond(self, status, data, content_type='application/json', cookie=False, filename=None):
        body = json.dumps(data).encode() if content_type == 'application/json' else data
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie:
            self.send_header('Set-Cookie', f'qf_session={self.server.token}; HttpOnly; SameSite=Strict; Path=/')
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_PATCH(self):
        self.handle_request()

    def do_DELETE(self):
        self.handle_request()

    def handle_request(self):
        try:
            host = self.headers.get('Host', '')
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if host not in allowed:
                raise RequestError(403, 'Localhost access only.')
            path = urlparse(self.path).path
            if path.startswith('/api/'):
                cookie = SimpleCookie(self.headers.get('Cookie', ''))
                token = cookie.get('qf_session')
                if not token or not secrets.compare_digest(token.value, self.server.token):
                    raise RequestError(401, 'Open the local app to start a session.')
                payload = None
                if self.command != 'GET':
                    if self.headers.get('Origin') != f'http://{host}':
                        raise RequestError(403, 'Same-origin requests required.')
                    if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                        raise RequestError(415, 'Only JSON text is accepted. Uploads are disabled.')
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 150000:
                        raise RequestError(413, 'Request is too large or empty.')
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict):
                        raise RequestError(400, 'Expected a JSON object.')
                self.api(path, payload)
                return
            if self.command != 'GET':
                raise RequestError(405, 'Method not allowed.')
            if path == '/vendor/lucide.js':
                target = ROOT.parent / 'node_modules/lucide/dist/umd/lucide.js'
            else:
                target = (ROOT / 'static' / ('index.html' if path == '/' else path.lstrip('/'))).resolve()
                if not target.is_relative_to(ROOT / 'static'):
                    raise RequestError(404, 'Not found.')
            if not target.is_file():
                raise RequestError(404, 'Not found.')
            kind = mimetypes.guess_type(target)[0] or 'application/octet-stream'
            self.respond(200, target.read_bytes(), kind, cookie=path == '/')
        except RequestError as error:
            self.respond(error.status, {'error': error.message})
        except (ValueError, TypeError, KeyError):
            self.respond(400, {'error': 'Invalid request data.'})
        except Exception:
            self.respond(500, {'error': 'Operation failed. Your saved case is unchanged.'})

    def api(self, path, payload):
        if path == '/api/catalogue' and self.command == 'GET':
            self.respond(200, {'products': list(CATALOGUE.values()), 'mode': 'offline', 'fixture_date': '2026-09-17'})
            return
        with sqlite3.connect(self.server.database) as connection:
            if self.command != 'GET':
                connection.execute('BEGIN IMMEDIATE')
            if path == '/api/cases' and self.command == 'GET':
                cases = [enrich(json.loads(row[0])) for row in connection.execute('SELECT data FROM cases ORDER BY rowid DESC')]
                self.respond(200, {'cases': cases})
                return
            if path == '/api/cases' and self.command == 'POST':
                text = payload.get('text', '')
                if not isinstance(text, str) or not 0 < len(text.strip()) <= 20000:
                    raise RequestError(400, 'Enter 1 to 20,000 characters of enquiry text.')
                if payload.get('customer_confirmed') is not True:
                    raise RequestError(400, 'Confirm this enquiry belongs to Acme Facilities.')
                title, recipient = payload.get('title', '').strip(), payload.get('recipient', '').strip()
                if not title or len(title) > 120 or not recipient or len(recipient) > 120:
                    raise RequestError(400, 'Provide a subject and recipient name, each up to 120 characters.')
                case = {'id': 'Q-' + secrets.token_hex(3).upper(), 'title': title, 'text': text,
                        'recipient': recipient, 'revision': 1, 'lines': extract(text),
                        'reviewed': False, 'delivery_accepted': False,
                        'created': datetime.now(timezone.utc).isoformat(),
                        'history': [{'revision': 1, 'action': 'Enquiry created', 'time': datetime.now(timezone.utc).isoformat()}]}
                if len(case['lines']) > 20:
                    raise RequestError(400, 'Maximum 20 requested product lines.')
                connection.execute('INSERT INTO cases (id,data) VALUES (?,?)', (case['id'], json.dumps(case)))
                connection.commit()
                self.respond(201, enrich(case))
                return
            match = re.fullmatch(r'/api/cases/(Q-[A-F0-9]{6})(?:/(review|pdf|email))?', path)
            if not match:
                raise RequestError(404, 'Not found.')
            case_id, action = match.groups()
            row = connection.execute('SELECT data FROM cases WHERE id=?', (case_id,)).fetchone()
            if not row:
                raise RequestError(404, 'Case not found.')
            case = json.loads(row[0])
            if self.command == 'GET':
                enriched = enrich(case)
                if action in ('pdf', 'email'):
                    if enriched['evaluation']['blocks'] or (enriched['evaluation']['stock'] and not case['delivery_accepted']):
                        raise RequestError(409, 'Resolve product and delivery questions before export.')
                    quote = public_quote(enriched)
                    if action == 'pdf':
                        self.respond(200, render_pdf(quote), 'application/pdf', filename=f'{case_id}-r{case["revision"]}.pdf')
                    else:
                        self.respond(200, email_draft(quote).encode(), 'text/plain; charset=utf-8', filename=f'{case_id}-email.txt')
                elif action is None:
                    self.respond(200, enriched)
                else:
                    raise RequestError(405, 'Method not allowed.')
                return
            if payload.get('revision') != case['revision']:
                raise RequestError(409, 'This case changed. Reload it before saving.')
            if self.command == 'DELETE' and action is None:
                connection.execute('DELETE FROM cases WHERE id=?', (case_id,))
                connection.commit()
                self.respond(200, {'deleted': case_id})
                return
            if self.command == 'PATCH' and action is None:
                if set(payload) - {'revision', 'lines', 'delivery_accepted', 'recipient'}:
                    raise RequestError(400, 'Only lines, recipient and delivery acceptance can be edited.')
                if 'lines' in payload:
                    if not isinstance(payload['lines'], list) or not 1 <= len(payload['lines']) <= 20 or not all(isinstance(x, dict) for x in payload['lines']):
                        raise RequestError(400, 'Provide between 1 and 20 product lines.')
                    case['lines'] = payload['lines']
                    case['delivery_accepted'] = False
                if 'recipient' in payload:
                    recipient = payload['recipient']
                    if not isinstance(recipient, str) or not 0 < len(recipient.strip()) <= 120:
                        raise RequestError(400, 'Recipient is required, up to 120 characters.')
                    case['recipient'] = recipient.strip()
                if 'delivery_accepted' in payload:
                    if not isinstance(payload['delivery_accepted'], bool):
                        raise RequestError(400, 'Invalid delivery acceptance.')
                    case['delivery_accepted'] = payload['delivery_accepted']
                case['revision'] += 1
                case['reviewed'] = False
                event = 'Case revised; prior review invalidated'
            elif self.command == 'POST' and action == 'review':
                evaluation = enrich(dict(case))['evaluation']
                if evaluation['status'] != 'Ready for review':
                    raise RequestError(409, 'Resolve questions and commercial approvals before final review.')
                if case['reviewed']:
                    self.respond(200, enrich(case))
                    return
                case['reviewed'] = True
                event = 'Reviewed by local demo operator'
            else:
                raise RequestError(405, 'Method not allowed.')
            case['history'].append({'revision': case['revision'], 'action': event, 'time': datetime.now(timezone.utc).isoformat()})
            # Persist only case inputs and history; recalculate commercial values on read.
            connection.execute('UPDATE cases SET data=? WHERE id=?', (json.dumps(case), case_id))
            connection.commit()
            self.respond(200, enrich(case))


def make_server(port=8765, database=None):
    database = Path(database or ROOT / 'data/cases.db')
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.database, server.token = database, secrets.token_urlsafe(32)
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = make_server(args.port)
    print(f'QuoteFlow local demo: http://127.0.0.1:{server.server_port}', flush=True)
    server.serve_forever()
