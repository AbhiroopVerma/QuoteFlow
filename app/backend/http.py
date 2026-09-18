"""Single-user localhost sandbox; never bind this demo to a public interface."""

import json
import mimetypes
import re
import secrets
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from app.backend.domain import CATALOGUE, evaluate, extract, public_quote, quote_hash
from app.backend.documents import email_draft, render_pdf
from app.backend.workflow import ACTORS, WorkflowError, approval_state, current_tasks, request_approvals, decide

from app.database import repository as store

ROOT = Path(__file__).resolve().parents[1]


class RequestError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def enrich(case):
    case['evaluation'] = evaluate(case['lines'], delivery_accepted=case['delivery_accepted'])
    if re.search(r'\b(USD|EUR|GBP|MYR|AUD)\b', case['text'], re.I):
        case['evaluation']['blocks'].append('Only SGD is in scope. Correct the source enquiry to continue.')
        case['evaluation']['status'] = 'Needs clarification'
    case['approval_state'] = approval_state(case, case['evaluation']['approvers'])
    case['current_approvals'] = current_tasks(case)
    if case['evaluation']['status'] == 'Awaiting approval':
        if case['approval_state'] == 'approved':
            case['evaluation']['status'] = 'Ready for review'
        elif case['approval_state'] == 'rejected':
            case['evaluation']['status'] = 'Changes requested'
    if case['evaluation']['status'] != 'Ready for review':
        case['reviewed'] = False
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
                target = (ROOT / 'frontend' / ('index.html' if path == '/' else path.lstrip('/'))).resolve()
                if not target.is_relative_to(ROOT / 'frontend'):
                    raise RequestError(404, 'Not found.')
            if not target.is_file():
                raise RequestError(404, 'Not found.')
            kind = mimetypes.guess_type(target)[0] or 'application/octet-stream'
            self.respond(200, target.read_bytes(), kind, cookie=path == '/')
        except (RequestError, WorkflowError) as error:
            self.respond(error.status, {'error': error.message})
        except (ValueError, TypeError, KeyError):
            self.respond(400, {'error': 'Invalid request data.'})
        except Exception:
            self.respond(500, {'error': 'Operation failed. Your saved case is unchanged.'})

    def api(self, path, payload):
        self.actor = ACTORS.get(self.headers.get('X-Demo-Actor', 'admin'))
        if self.actor is None:
            raise RequestError(403, 'Unknown demo persona.')
        if path == '/api/personas' and self.command == 'GET':
            self.respond(200, {'actors': list(ACTORS.values()), 'simulated': True})
            return
        if path == '/api/catalogue' and self.command == 'GET':
            self.respond(200, {'products': list(CATALOGUE.values()), 'mode': 'offline', 'fixture_date': '2026-09-17'})
            return
        with store.transaction(self.server.database, write=self.command != 'GET') as connection:
            if path == '/api/cases' and self.command == 'GET':
                cases = [enrich(case) for case in store.list_cases(connection)]
                self.respond(200, {'cases': cases})
                return
            if path == '/api/cases' and self.command == 'POST':
                self.require_admin()
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
                        'reviewed': False, 'delivery_accepted': False, 'approvals': [],
                        'created_by': self.actor['id'],
                        'created': datetime.now(timezone.utc).isoformat(),
                        'history': [{'revision': 1, 'action': 'Enquiry created', 'time': datetime.now(timezone.utc).isoformat()}]}
                if len(case['lines']) > 20:
                    raise RequestError(400, 'Maximum 20 requested product lines.')
                store.create_case(connection, case)
                store.save_snapshot(connection, case)
                connection.commit()
                self.respond(201, enrich(case))
                return
            match = re.fullmatch(r'/api/cases/(Q-[A-F0-9]{6})(?:/(review|pdf|email|request-approvals|decision|revisions))?', path)
            if not match:
                raise RequestError(404, 'Not found.')
            case_id, action = match.groups()
            case = store.get_case(connection, case_id)
            if case is None:
                raise RequestError(404, 'Case not found.')
            if self.command == 'GET':
                if action == 'revisions':
                    revisions = store.list_revisions(connection, case_id)
                    self.respond(200, {'revisions': revisions})
                    return
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
                self.require_admin()
                store.delete_case(connection, case_id)
                connection.commit()
                self.respond(200, {'deleted': case_id})
                return
            if self.command == 'PATCH' and action is None:
                self.require_admin()
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
                event = 'Case revised; prior approvals and review invalidated'
                store.save_snapshot(connection, case)
            elif self.command == 'POST' and action in ('request-approvals', 'decision'):
                evaluation = enrich(dict(case))['evaluation']
                if evaluation['blocks'] or (evaluation['stock'] and not case['delivery_accepted']):
                    raise RequestError(409, 'Resolve all product and delivery questions before approval.')
                if not evaluation['approvers']:
                    raise RequestError(409, 'This revision does not require commercial approval.')
                if action == 'request-approvals':
                    changed = request_approvals(case, self.actor, evaluation['approvers'])
                    event = 'Demo commercial approval requested'
                else:
                    changed = decide(case, self.actor, payload.get('decision'), payload.get('reason'))
                    event = f'Demo {self.actor["role"]}: {payload["decision"]} - {payload["reason"].strip()}'
                if not changed:
                    self.respond(200, enrich(case))
                    return
            elif self.command == 'POST' and action == 'review':
                self.require_admin()
                evaluation = enrich(dict(case))['evaluation']
                if evaluation['status'] != 'Ready for review':
                    raise RequestError(409, 'Resolve questions and commercial approvals before final review.')
                if case['reviewed']:
                    self.respond(200, enrich(case))
                    return
                case['reviewed'] = True
                event = 'Final review by Demo Administrator'
            else:
                raise RequestError(405, 'Method not allowed.')
            case['history'].append({'revision': case['revision'], 'action': event,
                                    'actor': self.actor['id'], 'time': datetime.now(timezone.utc).isoformat()})
            # Persist only case inputs and history; recalculate commercial values on read.
            store.update_case(connection, case)
            connection.commit()
            self.respond(200, enrich(case))

    def require_admin(self):
        if self.actor['role'] != 'Sales Administrator':
            raise RequestError(403, 'Only the demo administrator may edit or review quotes.')

def make_server(port=8765, database=None):
    database = store.initialize(database or store.DEFAULT_PATH)
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.database, server.token = database, secrets.token_urlsafe(32)
    return server
