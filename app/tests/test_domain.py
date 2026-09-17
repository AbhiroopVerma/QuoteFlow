import copy
import json
import unittest
from pathlib import Path

from app.domain import CATALOGUE, evaluate, extract, public_quote


class DomainTests(unittest.TestCase):
    def test_golden_monetary_expectations(self):
        suite = json.loads(Path('docs/demo/golden-cases.json').read_text())
        for case in suite['cases']:
            if 'subtotal' not in case['expected']:
                continue
            with self.subTest(case=case['id']):
                catalogue = copy.deepcopy(CATALOGUE)
                for sku, patch in case.get('overrides', {}).items():
                    catalogue[sku].update(patch)
                result = evaluate(case['lines'], catalogue=catalogue, delivery_accepted=True)
                for field in ('subtotal', 'tax', 'total', 'approvers'):
                    self.assertEqual(result[field], case['expected'][field])

    def test_extract_happy_path(self):
        lines = extract('Please quote 50 EL-MCB-1P16 and 20 BX-IP65-2015-A.')
        self.assertEqual([(x['sku'], x['qty']) for x in lines],
                         [('EL-MCB-1P16', 50), ('BX-IP65-2015-A', 20)])

    def test_missing_material_remains_unresolved(self):
        lines = extract('20 IP65 junction boxes 200 x 150 mm')
        self.assertEqual(len(lines), 1)
        self.assertIsNone(lines[0]['sku'])
        self.assertEqual(len(lines[0]['candidates']), 2)

    def test_missing_curve_remains_unresolved(self):
        self.assertIsNone(extract('50 16A single-pole MCB')[0]['sku'])

    def test_unknown_text_never_disappears(self):
        lines = extract('12 mystery widgets')
        self.assertIsNone(lines[0]['sku'])

    def test_mixed_unknown_line_is_preserved(self):
        lines = extract('50 EL-MCB-1P16 and 12 mystery widgets')
        self.assertEqual(len(lines), 2)
        self.assertIsNone(lines[1]['sku'])

    def test_wrong_unit_not_silently_converted(self):
        lines = extract('250 metres of CBL-CU25-R100')
        result = evaluate(lines)
        self.assertTrue(any('unit' in x.lower() for x in result['blocks']))

    def test_pack_and_zero_price_block(self):
        self.assertTrue(evaluate([{'sku': 'EL-MCB-1P16', 'qty': 11}])['blocks'])
        self.assertTrue(evaluate([{'sku': 'EL-MCB-1P16', 'qty': 10, 'discretionary_percent': '100'}])['blocks'])

    def test_contract_stacking_block(self):
        result = evaluate([{'sku': 'CBL-CU25-R100', 'qty': 6, 'discretionary_percent': '5'}])
        self.assertTrue(result['blocks'])

    def test_stock_requires_consent(self):
        lines = [{'sku': 'CBL-CU25-R100', 'qty': 12}]
        self.assertEqual(evaluate(lines)['status'], 'Needs clarification')
        self.assertEqual(evaluate(lines, delivery_accepted=True)['status'], 'Ready for review')

    def test_impossible_stock_still_blocks_with_consent(self):
        result = evaluate([{'sku': 'EL-MCB-1P16', 'qty': 10000}], delivery_accepted=True)
        self.assertTrue(result['blocks'])

    def test_invalid_numeric_inputs_fail_closed(self):
        for qty in [True, -1, 0, 'NaN', 1.5, 'Infinity']:
            self.assertTrue(evaluate([{'sku': 'EL-MCB-1P16', 'qty': qty}])['blocks'])
        for discount in ['NaN', 'Infinity', '-1', '101']:
            self.assertTrue(evaluate([{'sku': 'EL-MCB-1P16', 'qty': 10, 'discretionary_percent': discount}])['blocks'])

    def test_export_has_no_internal_costs(self):
        result = evaluate([{'sku': 'EL-MCB-1P16', 'qty': 50}])
        case = {'id': 'Q-001', 'revision': 1, 'evaluation': result,
                'reviewed': False, 'recipient': 'Demo purchasing team'}
        exported = json.dumps(public_quote(case))
        for forbidden in ['margin', 'cost', 'approvers', 'discretionary_percent']:
            self.assertNotIn(forbidden, exported)


if __name__ == '__main__':
    unittest.main()
