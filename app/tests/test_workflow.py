import copy
import unittest

from app.backend.workflow import ACTORS, WorkflowError, approval_state, request_approvals, decide


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.case = {'revision': 1, 'lines': [{'sku': 'EL-MCB-1P16', 'qty': 10,
                      'discretionary_percent': '20'}], 'recipient': 'Demo buyer',
                     'delivery_accepted': False, 'text': '10 MCB', 'approvals': []}

    def test_approval_bound_to_current_inputs(self):
        request_approvals(self.case, ACTORS['admin'], ['Finance Approver'])
        decide(self.case, ACTORS['finance'], 'approved', 'Demo exception accepted')
        self.assertEqual(approval_state(self.case, ['Finance Approver']), 'approved')
        self.case['lines'][0]['qty'] = 20
        self.assertEqual(approval_state(self.case, ['Finance Approver']), 'pending')

    def test_union_requires_both_roles(self):
        roles = ['Sales Manager', 'Finance Approver']
        request_approvals(self.case, ACTORS['admin'], roles)
        decide(self.case, ACTORS['finance'], 'approved', 'Finance agrees')
        self.assertEqual(approval_state(self.case, roles), 'pending')
        decide(self.case, ACTORS['manager'], 'approved', 'Manager agrees')
        self.assertEqual(approval_state(self.case, roles), 'approved')

    def test_rejection_cannot_be_overwritten(self):
        request_approvals(self.case, ACTORS['admin'], ['Finance Approver'])
        decide(self.case, ACTORS['finance'], 'rejected', 'Reduce the discount')
        self.assertEqual(approval_state(self.case, ['Finance Approver']), 'rejected')
        with self.assertRaises(WorkflowError):
            decide(self.case, ACTORS['finance'], 'approved', 'Changed my mind')

    def test_repeated_identical_decision_is_idempotent(self):
        request_approvals(self.case, ACTORS['admin'], ['Finance Approver'])
        self.assertTrue(decide(self.case, ACTORS['finance'], 'approved', 'Accepted'))
        previous = copy.deepcopy(self.case)
        self.assertFalse(decide(self.case, ACTORS['finance'], 'approved', 'Accepted'))
        self.assertEqual(previous, self.case)

    def test_cannot_self_approve_even_if_role_changes(self):
        request_approvals(self.case, ACTORS['admin'], ['Finance Approver'])
        impersonated = {**ACTORS['finance'], 'id': 'admin'}
        with self.assertRaises(WorkflowError):
            decide(self.case, impersonated, 'approved', 'Accepted')

    def test_wrong_role_and_missing_reason_rejected(self):
        request_approvals(self.case, ACTORS['admin'], ['Finance Approver'])
        with self.assertRaises(WorkflowError):
            decide(self.case, ACTORS['manager'], 'approved', 'Accepted')
        with self.assertRaises(WorkflowError):
            decide(self.case, ACTORS['finance'], 'rejected', '  ')

    def test_request_retries_do_not_reset_decisions(self):
        request_approvals(self.case, ACTORS['admin'], ['Finance Approver'])
        decide(self.case, ACTORS['finance'], 'rejected', 'Reduce discount')
        self.assertFalse(request_approvals(self.case, ACTORS['admin'], ['Finance Approver']))
        self.assertEqual(approval_state(self.case, ['Finance Approver']), 'rejected')
