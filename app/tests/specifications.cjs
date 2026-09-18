const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const specs = require('../frontend/js/specifications.js');
const catalogue = JSON.parse(fs.readFileSync('docs/demo/fixtures.json', 'utf8')).products;

test('every fixture has labelled specification icons', () => {
  for (const product of catalogue) {
    const html = specs.render(product);
    assert.match(html, /data-lucide=/);
    assert.match(html, /title=/);
    assert.match(html, /Pack size/);
  }
});
test('specifications carry catalogue values, not inferred ratings', () => {
  const html = specs.render(catalogue.find(p => p.sku === 'EL-MCB-1P16'));
  assert.match(html, /16 A/);
  assert.match(html, /1 pole/);
  assert.match(html, /C curve/);
  assert.doesNotMatch(html, /certified|6000|voltage/i);
});
test('absent products have no invented specifications', () => {
  assert.equal(specs.render(null), '');
});
test('specification values are escaped', () => {
  const html = specs.render({specifications: {material:'<img src=x onerror=alert(1)>'}, pack:5, uom:'EA'});
  assert.doesNotMatch(html, /<img/);
  assert.match(html, /&lt;img/);
});
