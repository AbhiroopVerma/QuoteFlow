"""Revision-bound approval rehearsal. Personas are not authenticated identities."""

import hashlib
import json
from datetime import datetime, timezone

ACTORS = {
    'admin': {'id': 'admin', 'name': 'Demo Administrator', 'role': 'Sales Administrator'},
    'manager': {'id': 'manager', 'name': 'Demo Sales Manager', 'role': 'Sales Manager'},
    'finance': {'id': 'finance', 'name': 'Demo Finance Approver', 'role': 'Finance Approver'},
}


class WorkflowError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def input_hash(case):
    fields = {key: case.get(key) for key in ('revision', 'lines', 'recipient', 'text', 'delivery_accepted')}
    fields['policy_version'] = 'demo-v1'
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def current_tasks(case):
    fingerprint = input_hash(case)
    return [task for task in case.get('approvals', [])
            if task['revision'] == case['revision'] and task['input_hash'] == fingerprint]


def approval_state(case, roles):
    tasks = {task['role']: task for task in current_tasks(case)}
    if any(tasks.get(role, {}).get('status') == 'rejected' for role in roles):
        return 'rejected'
    if all(tasks.get(role, {}).get('status') == 'approved' for role in roles):
        return 'approved'
    return 'pending'


def request_approvals(case, actor, roles):
    if actor['role'] != 'Sales Administrator':
        raise WorkflowError(403, 'Only the demo administrator can request approval.')
    existing = {task['role'] for task in current_tasks(case)}
    changed = False
    for role in roles:
        if role in existing:
            continue
        case.setdefault('approvals', []).append({
            'revision': case['revision'], 'input_hash': input_hash(case),
            'role': role, 'status': 'pending', 'requested_by': actor['id'],
            'requested_at': datetime.now(timezone.utc).isoformat(),
        })
        changed = True
    return changed


def decide(case, actor, decision, reason):
    if actor['role'] not in ('Sales Manager', 'Finance Approver'):
        raise WorkflowError(403, 'Select the required demo approver persona.')
    if decision not in ('approved', 'rejected') or not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 1000:
        raise WorkflowError(400, 'Provide an approval/rejection and a reason of 1 to 1,000 characters.')
    task = next((task for task in current_tasks(case) if task['role'] == actor['role']), None)
    if not task or task['requested_by'] == actor['id']:
        raise WorkflowError(403, 'No eligible approval task for this demo persona.')
    reason = reason.strip()
    if task['status'] != 'pending':
        if task['status'] == decision and task.get('decided_by') == actor['id'] and task.get('reason') == reason:
            return False
        raise WorkflowError(409, 'This task already has a decision. Revise the quote to request another.')
    task.update(status=decision, reason=reason, decided_by=actor['id'],
                decided_at=datetime.now(timezone.utc).isoformat())
    return True
