"""Deterministic, offline quotation rules for the synthetic demo catalogue."""

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

FIXTURES = json.loads((Path(__file__).resolve().parents[1] / 'docs/demo/fixtures.json').read_text())
CATALOGUE = {p['sku']: p for p in FIXTURES['products']}
D = Decimal


def money(value):
    return f'{value.quantize(D("0.01"), rounding=ROUND_HALF_UP):.2f}'


def extract(text):
    """Bounded catalogue grammar; uncertain descriptions remain editable lines."""
    lines = []
    for chunk in re.split(r'\n|;|\band\s+(?=\d)|,\s*(?=\d)', text, flags=re.I):
        chunk = chunk.strip()
        if not chunk:
            continue
        exact = next((sku for sku in CATALOGUE if re.search(r'(?<![\w-])' + re.escape(sku) + r'(?![\w-])', chunk, re.I)), None)
        low = chunk.lower()
        candidates, question = [], ''
        if exact:
            candidates = [exact]
        elif 'box' in low or 'boxes' in low:
            candidates = ['BX-IP65-2015-A', 'BX-IP65-2015-M']
            if 'abs' in low:
                candidates = candidates[:1]
            elif 'metal' in low:
                candidates = candidates[1:]
            if not ('ip65' in low and re.search(r'200\s*[x×]\s*150', low)):
                question = 'Confirm IP rating and box dimensions.'
            elif len(candidates) > 1:
                question = 'Do you need ABS or metal boxes?'
        elif 'mcb' in low or 'breaker' in low:
            candidates = ['EL-MCB-1P16']
            if not (re.search(r'16\s*a\b', low) and re.search(r'(single[ -]?pole|1[ -]?pole|1p)', low) and re.search(r'c[ -]?curve', low)):
                question = 'Confirm 16A, single pole and C curve.'
        elif 'cable' in low:
            candidates = ['CBL-CU25-R100']
            if not ('copper' in low and '2.5' in low and re.search(r'100\s*(m|metre|meter)', low)):
                question = 'Confirm copper, 2.5 mm2 and a 100 m roll.'
        elif 'panel' in low or 'led' in low:
            candidates = ['LT-PNL-32W-4K' if '32w' in low else 'LT-PNL-36W-4K']
            if not (re.search(r'(32|36)\s*w', low) and ('4000k' in low or '4k' in low)):
                question = 'Confirm wattage and 4000K colour temperature.'
        elif not re.search(r'\d', chunk) and re.match(r'^(hi|hello|dear|thanks|regards|subject:|acme|please quote)\b', low):
            continue
        prefix = chunk[:re.search(re.escape(exact), chunk, re.I).start()] if exact else chunk
        quantity = re.search(r'(?<![\w.])(-?\d+(?:\.\d+)?)\s*(?:pcs|pieces|units|rolls|ea|x)?\b', prefix, re.I)
        qty = float(quantity.group(1)) if quantity else None
        if qty is not None and qty.is_integer():
            qty = int(qty)
        sku = candidates[0] if len(candidates) == 1 and not question else None
        discount = re.search(r'(?:another|extra|additional|with)\s+(\d+(?:\.\d+)?)\s*(?:percent|%)', low)
        uom = CATALOGUE[sku]['uom'] if sku else 'EA'
        if re.search(r'\d\s*(?:metres|meters)\s+(?:of\s+)?CBL', chunk, re.I):
            uom = 'M'
        lines.append({'sku': sku, 'qty': qty, 'uom': uom,
                      'discretionary_percent': discount.group(1) if discount else '0',
                      'source': chunk, 'candidates': candidates,
                      'question': question or ('' if sku else 'Select a catalogue product or remove this out-of-scope line.')})
    return lines or [{'sku': None, 'qty': None, 'uom': 'EA', 'discretionary_percent': '0',
                      'source': text, 'candidates': [], 'question': 'Enter a quantity and catalogue product.'}]


def evaluate(lines, catalogue=None, delivery_accepted=False):
    catalogue = catalogue or CATALOGUE
    rows, blocks, stock, roles = [], [], [], set()
    subtotal = D(0)
    if not isinstance(lines, list) or not 1 <= len(lines) <= 20:
        return {'lines': [], 'blocks': ['Provide between 1 and 20 product lines.'],
                'stock': [], 'approvers': [], 'subtotal': '0.00', 'tax': '0.00',
                'total': '0.00', 'status': 'Needs clarification'}
    for index, line in enumerate(lines):
        label = f'Line {index + 1}'
        if not isinstance(line, dict):
            blocks.append(f'{label}: invalid line.')
            continue
        sku = line.get('sku')
        product = catalogue.get(sku) if isinstance(sku, str) else None
        if not product:
            blocks.append(f'{label}: confirm the product and required specifications.')
            continue
        if not product['active']:
            blocks.append(f'{label}: {sku} is discontinued. Confirm an alternative.')
            continue
        try:
            qty = D(str(line.get('qty')))
            extra = D(str(line.get('discretionary_percent', '0')))
            if not qty.is_finite() or not extra.is_finite():
                raise ValueError()
            if qty <= 0 or qty > 1000000 or qty != qty.to_integral_value() or not 0 <= extra <= 100:
                raise ValueError()
        except (InvalidOperation, ValueError):
            blocks.append(f'{label}: enter a positive whole quantity and discount from 0 to 100%.')
            continue
        if qty < product['moq'] or qty % product['pack']:
            blocks.append(f'{label}: quantity must be a multiple of {product["pack"]} (minimum {product["moq"]}).')
            continue
        if line.get('uom', product['uom']) != product['uom']:
            blocks.append(f'{label}: unit must be {product["uom"]}; no automatic conversion.')
            continue
        source_type = 'contract' if 'contract' in product else 'gold' if 'gold' in product else 'list'
        source = D(product[source_type])
        if source_type == 'contract' and extra:
            blocks.append(f'{label}: contract pricing cannot stack with additional discounts.')
            continue
        volume = D('0.03') if source_type != 'contract' and product['uom'] == 'EA' and qty >= 50 else D(0)
        net = D(money(D(money(source * (1 - volume))) * (1 - extra / 100)))
        if net <= 0:
            blocks.append(f'{label}: zero or negative unit prices are not allowed.')
            continue
        discount = 100 * (1 - net / source)
        margin = 100 * (net - D(product['cost'])) / net
        if discount > 12 or margin < 15:
            roles.add('Finance Approver')
        if 5 < discount <= 12 or 15 <= margin < 20:
            roles.add('Sales Manager')
        if qty > product['atp']:
            if qty > product['atp'] + product['inbound']:
                blocks.append(f'{label}: insufficient confirmed stock, including inbound supply.')
            else:
                stock.append({'sku': sku, 'now': product['atp'], 'later': int(qty) - product['atp'], 'eta': product['eta']})
        amount = net * qty
        subtotal += amount
        rows.append({'sku': sku, 'name': product['name'], 'qty': int(qty), 'uom': product['uom'],
                     'source_type': source_type.title(), 'source_price': money(source),
                     'unit_price': money(net), 'amount': money(amount), 'margin': money(margin),
                     'effective_discount': money(discount), 'atp': product['atp'], 'cost': product['cost']})
    tax = D(money(subtotal * D('0.09')))
    total = subtotal + tax
    if total > 100000:
        roles.update(['Sales Manager', 'Finance Approver'])
    status = 'Needs clarification' if blocks or (stock and not delivery_accepted) else 'Awaiting approval' if roles else 'Ready for review'
    return {'lines': rows, 'blocks': blocks, 'stock': stock, 'approvers': sorted(roles),
            'subtotal': money(subtotal), 'tax': money(tax), 'total': money(total), 'status': status}


def public_quote(case):
    evaluation = case['evaluation']
    return {'id': case['id'], 'revision': case['revision'], 'draft': not case['reviewed'],
            'seller': FIXTURES['seller'], 'customer': FIXTURES['customer']['name'],
            'recipient': case.get('recipient', ''), 'currency': 'SGD', 'terms': 'Net 30',
            'fixture_date': '17 September 2026', 'valid_until': '24 September 2026',
            'lines': [{k: line[k] for k in ('sku', 'name', 'qty', 'uom', 'unit_price', 'amount')}
                      for line in evaluation['lines']],
            'subtotal': evaluation['subtotal'], 'tax': evaluation['tax'], 'total': evaluation['total'],
            'delivery': evaluation['stock'], 'freight': '0.00'}


def quote_hash(case):
    return hashlib.sha256(json.dumps(public_quote(case), sort_keys=True).encode()).hexdigest()
