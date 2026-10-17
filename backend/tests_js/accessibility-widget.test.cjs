const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { runInNewContext } = require('node:vm');
const source = readFileSync(require('node:path').join(__dirname, '../static/js/accessibility-widget.js'), 'utf8');

class Element {
  constructor(action = '') {
    this.action = action;
    this.dataset = { a11yAction: action };
    this.events = {};
    this.attributes = {};
    this.classes = new Set();
    this.classList = {
      toggle: (name, enabled) => enabled ? this.classes.add(name) : this.classes.delete(name),
      contains: name => this.classes.has(name),
    };
    this.hidden = false;
    this.textContent = '';
  }
  addEventListener(name, fn) { this.events[name] = fn; }
  setAttribute(name, value) { this.attributes[name] = value; }
  focus() { this.focused = true; }
  closest(selector) { return selector === '[data-a11y-action]' && this.action ? this : null; }
  contains(target) { return target === this || this.children?.includes(target); }
  querySelector(selector) { return this.selectors?.[selector] || null; }
  fire(name, event = {}) { this.events[name]?.(event); }
}

function setup(saved = null) {
  const root = new Element();
  root.style = { setProperty: (key, value) => { root.style[key] = value; } };
  const trigger = new Element();
  const panel = new Element();
  panel.hidden = true;
  const size = new Element();
  const actions = Object.fromEntries(['text-smaller', 'text-larger', 'contrast', 'links', 'motion', 'reset']
    .map(name => [name, new Element(name)]));
  const widget = new Element();
  widget.children = [trigger, panel, ...Object.values(actions)];
  widget.selectors = {
    '[data-a11y-trigger]': trigger,
    '.aw-accessibility__panel': panel,
    '[data-a11y-text-size]': size,
    ...Object.fromEntries(Object.entries(actions).map(([name, element]) => [`[data-a11y-action="${name}"]`, element])),
  };
  const document = new Element();
  document.documentElement = root;
  document.activeElement = trigger;
  document.querySelector = selector => selector === '[data-accessibility-widget]' ? widget : null;
  const events = [];
  const window = { dispatchEvent: event => events.push(event) };
  const store = new Map(saved ? [['wallstein.a11y.settings', JSON.stringify(saved)]] : []);
  const localStorage = {
    getItem: key => store.get(key) || null,
    setItem: (key, value) => store.set(key, value),
  };
  class CustomEvent { constructor(type, init) { this.type = type; this.detail = init.detail; } }
  runInNewContext(source, { document, window, localStorage, CustomEvent });
  return { root, trigger, panel, size, actions, document, events, store, widget };
}

test('stored display preferences are restored and update toggle states', () => {
  const s = setup({ fontScale: 1.2, highContrast: true, highlightLinks: true, reduceMotion: true });
  assert.equal(s.root.style['--aw-font-scale'], '1.2');
  for (const feature of ['aw-high-contrast', 'aw-highlight-links', 'user-reduced-motion']) assert.equal(s.root.classList.contains(feature), true);
  assert.equal(s.size.textContent, '120 %');
  assert.equal(s.actions.contrast.attributes['aria-pressed'], 'true');
  assert.equal(s.events.at(-1).detail.reduced, true);
});

test('menu opens accessibly and Escape closes it with focus restored', () => {
  const s = setup();
  s.trigger.fire('click');
  assert.equal(s.panel.hidden, false);
  assert.equal(s.trigger.attributes['aria-expanded'], 'true');
  assert.equal(s.trigger.attributes['aria-label'], 'Barrierefreiheit schließen');
  s.document.fire('keydown', { key: 'Escape' });
  assert.equal(s.panel.hidden, true);
  assert.equal(s.trigger.attributes['aria-expanded'], 'false');
  assert.equal(s.trigger.focused, true);
});

test('preferences can be changed, persisted and reset', () => {
  const s = setup();
  s.widget.fire('click', { target: s.actions['text-larger'] });
  s.widget.fire('click', { target: s.actions.contrast });
  assert.equal(s.root.style['--aw-font-scale'], '1.1');
  assert.equal(s.actions.contrast.attributes['aria-pressed'], 'true');
  assert.equal(JSON.parse(s.store.get('wallstein.a11y.settings')).highContrast, true);
  s.widget.fire('click', { target: s.actions.reset });
  assert.equal(s.root.classList.contains('aw-high-contrast'), false);
  assert.equal(s.size.textContent, '100 %');
});
