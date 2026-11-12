import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = name => readFileSync(new URL(name, import.meta.url), 'utf8');
const demo = read('demo.html');
const fields = read('field-states.html');

for (const file of ['components.css', 'demo.css', 'primitives.css']) {
  const css = read(file);
  assert(!/#[\da-f]{3,8}\b/i.test(css), `Hardcoded hex color in ${file}`);
  assert(demo.includes(css.trim()), `Standalone demo stylesheet is stale: ${file}`);
}
assert.match(read('primitives.css'), /@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*?animation:\s*none/);
for (const id of ['business', 'request', 'phone', 'email', 'pages']) {
  const expected = ['empty', 'filled', 'long-label', 'long-value', 'error', 'error-filled', 'disabled', 'focus', 'hover', 'loading'];
  for (const state of expected) {
    assert(fields.includes(`id="matrix-${id}-${state}"`), `Missing ${id}/${state}`);
  }
  assert(demo.includes(`for="${id}"`));
  assert(demo.includes(`id="${id}-error" hidden`));
}
for (const [id, type] of [['phone', 'tel'], ['email', 'email'], ['pages', 'number']]) {
  const input = demo.match(new RegExp(`<input id="${id}"[^>]*>`))?.[0];
  assert(input?.includes('dir="ltr"'));
  assert(input?.includes(`type="${type}"`));
}
assert.match(demo, /id="form-announcement"[^>]*role="alert"/);
console.log('CSS tokens, reduced motion, all 50 field cases and RTL form markup verified.');
