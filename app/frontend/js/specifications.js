'use strict';

// Display only catalogue-backed values; an icon never supplies a missing fact.
const QuoteFlowSpecifications = (() => {
  const fields = {
    current: ['zap', 'Current rating'],
    poles: ['split', 'Poles'],
    curve: ['activity', 'Trip curve'],
    cross_section: ['ruler', 'Conductor cross-section'],
    length: ['cable', 'Cable length'],
    power: ['lightbulb', 'Rated power'],
    temperature: ['thermometer', 'Colour temperature'],
    protection: ['shield-check', 'Ingress protection'],
    dimensions: ['ruler', 'Dimensions'],
    material: ['layers', 'Material']
  };
  const escape = value => String(value).replace(/[&<>"']/g, char => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  }[char]));

  function item(icon, label, value) {
    const description = escape(`${label}: ${value}`);
    return `<span class="specification" title="${description}" aria-label="${description}"><i data-lucide="${icon}" aria-hidden="true"></i><span>${escape(value)}</span></span>`;
  }

  function render(product) {
    if (!product) return '';
    const items = Object.entries(product.specifications || {})
      .filter(([key, value]) => fields[key] && value !== null && value !== '')
      .map(([key, value]) => item(...fields[key], value));
    if (product.pack) items.push(item('package', 'Pack size', `${product.pack} ${product.uom} / pack`));
    return items.length ? `<div class="specifications" role="group" aria-label="Product specifications">${items.join('')}</div>` : '';
  }

  return { render };
})();

if (typeof module !== 'undefined') module.exports = QuoteFlowSpecifications;
