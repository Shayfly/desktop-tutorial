import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const css = readFileSync(new URL('./tokens.css', import.meta.url), 'utf8');
const pairs = [
  ['s-text', 's-bg', 's-surface'],
  ['s-text-muted', 's-bg', 's-surface'],
  ['s-accent', 's-bg', 's-surface'],
  ['s-danger', 's-bg', 's-surface'],
  ['s-success', 's-bg', 's-surface'],
  ['s-warning', 's-bg', 's-surface'],
  ['c-btn-primary-fg', 'c-btn-primary-bg', 'c-btn-primary-hover', 'c-btn-primary-active'],
  ['c-btn-neutral-fg', 'c-btn-secondary-bg', 'c-btn-secondary-hover', 'c-btn-secondary-active',
    'c-btn-quiet-bg', 'c-btn-quiet-hover', 'c-btn-quiet-active'],
  ['c-btn-error-fg', 'c-btn-error-bg'],
  ['c-field-fg', 'c-field-bg'],
  ['c-field-hint', 'c-field-bg'],
  ['c-tag-fg', 'c-tag-bg'],
];

function properties(block) {
  return Object.fromEntries([...block.matchAll(/--([\w-]+):\s*([^;]+);/g)]
    .map(([, name, value]) => [name, value.trim()]));
}

function rgb(tokens, name) {
  const value = tokens[name];
  assert(value, `Missing token --${name}`);
  const alias = value.match(/^var\(--([\w-]+)\)$/);
  if (alias) return rgb(tokens, alias[1]);
  assert.match(value, /^#[0-9a-f]{6}$/i);
  return value.slice(1).match(/../g).map(channel => parseInt(channel, 16) / 255);
}

function luminance(rgb) {
  const linear = rgb.map(channel => channel <= 0.04045
    ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4);
  return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
}

const base = properties(css.slice(0, css.indexOf('[data-theme="dark"]')));
const dark = properties(css.match(/\[data-theme="dark"\]\s*\{([^}]+)\}/)[1]);
const auto = properties(css.match(/:root:not\(\[data-theme\]\)\s*\{([^}]+)\}/)[1]);
assert.deepEqual(auto, dark, 'Automatic and explicit dark themes must match');

function ratio(a, b) {
  const levels = [luminance(a), luminance(b)];
  return (Math.max(...levels) + 0.05) / (Math.min(...levels) + 0.05);
}

const scores = { active: [], disabled: [] };
const failures = [];
function check(group, label, value, threshold) {
  scores[group].push(value);
  if (value < threshold) failures.push(`${label}: ${value.toFixed(2)}:1 (minimum ${threshold}:1)`);
}

for (const [theme, tokens] of [['light', base], ['dark', { ...base, ...dark }]]) {
  for (const [foreground, ...backgrounds] of pairs) {
    for (const background of backgrounds) {
      check('active', `${theme}/${foreground}/${background}`,
        ratio(rgb(tokens, foreground), rgb(tokens, background)), 4.5);
    }
  }
  const opacity = Number(tokens['c-disabled-opacity']);
  for (const underlay of ['s-bg', 's-surface']) {
    const baseColor = rgb(tokens, underlay);
    const blend = color => rgb(tokens, color).map((channel, index) =>
      channel * opacity + baseColor[index] * (1 - opacity));
    check('disabled', `${theme}/disabled/${underlay}`,
      ratio(blend('s-text'), blend('s-surface')), 3);
  }
}
assert.equal(failures.length, 0, failures.join('\n'));
for (const [group, ratios] of Object.entries(scores)) {
  console.log(`${group}: ${ratios.length} passed, minimum ${Math.min(...ratios).toFixed(2)}:1`);
}
