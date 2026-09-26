const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { runInNewContext } = require('node:vm');
const source = readFileSync(require('node:path').join(__dirname, '../static/js/hero-slider.js'), 'utf8');

class Element {
  constructor() {
    this.events = {};
    this.attributes = {};
    this.children = [];
    this.classes = new Set();
    this.classList = {
      add: name => this.classes.add(name),
      toggle: (name, enabled) => enabled ? this.classes.add(name) : this.classes.delete(name),
    };
  }
  matches() { return Boolean(this.keyboardFocus); }
  setPointerCapture() {}
  addEventListener(name, fn) { this.events[name] = fn; }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
  contains(target) { return this === target || this.children.some(child => child.contains(target)); }
  querySelector(selector) { return this.selectors?.[selector] || null; }
  querySelectorAll(selector) { return this.groups?.[selector] || []; }
  fire(name, event = {}) { this.events[name]?.(event); }
}
function setup(count, reducedMotion = false, interval = 4) {
  const timers = new Map();
  let timerId = 0;
  const images = Array.from({ length: count }, () => Object.assign(new Element(), { complete: true, naturalWidth: 1600, loading: 'lazy' }));
  const slides = images.map(image => Object.assign(new Element(), {
    hidden: true, selectors: { '[data-hero-image]': image }, children: [image],
  }));
  const controls = Object.assign(new Element(), { hidden: true });
  const previous = new Element();
  const next = new Element();
  const status = new Element();
  const dots = slides.map(() => new Element());
  controls.selectors = { '[data-hero-previous]': previous, '[data-hero-next]': next, '[data-hero-status]': status };
  controls.groups = { '[data-hero-dot]': dots };
  controls.children = [previous, next, status, ...dots];
  const slider = Object.assign(new Element(), {
    dataset: { interval: String(interval) },
    children: [controls, ...slides],
    selectors: { '[data-hero-controls]': count > 1 ? controls : null },
    groups: { '[data-hero-slide]': slides, '[data-hero-image]': images },
  });
  const document = Object.assign(new Element(), { hidden: false, activeElement: null, groups: { '[data-hero-slider]': [slider] } });
  next.focus = () => { document.activeElement = next; next.keyboardFocus = true; slider.fire('focusin', { target: next }); };
  const motion = Object.assign(new Element(), { matches: reducedMotion });
  const delays = [];
  const window = Object.assign(new Element(), {
    getComputedStyle: () => ({ transitionDuration: reducedMotion ? '0s' : '0.6s' }),
    matchMedia: () => motion,
    setTimeout: (fn, delay) => { delays.push(delay); timers.set(++timerId, fn); return timerId; },
    clearTimeout: id => timers.delete(id),
  });
  runInNewContext(source, { document, window });
  const tick = () => { const [id, fn] = timers.entries().next().value; timers.delete(id); fn(); };
  return { slider, slides, images, previous, next, status, dots, controls, timers, tick, document, motion, window, delays, reinitialize: () => runInNewContext(source, { document, window }) };
}
const active = s => s.slides.map(slide => slide.classes.has('is-active'));

test('zero or one slide has no timer or controls', () => {
  for (const count of [0, 1]) {
    const s = setup(count);
    assert.equal(s.controls.hidden, true);
    assert.equal(s.timers.size, 0);
  }
});
test('manual navigation wraps and hides inactive panels from keyboard and screen readers', () => {
  const s = setup(3);
  s.previous.fire('click');
  assert.deepEqual(active(s), [false, false, true]);
  assert.deepEqual(s.slides.map(x => x.inert), [true, true, false]);
  assert.equal(s.slides[0].attributes['aria-hidden'], 'true');
  s.next.fire('click');
  assert.deepEqual(active(s), [true, false, false]);
  assert.equal(s.status.textContent, 'Slide 1 von 3');
});
test('dots select slides and update current indicator', () => {
  const s = setup(3);
  s.dots[2].fire('click');
  assert.deepEqual(active(s), [false, false, true]);
  assert.equal(s.dots[2].attributes['aria-current'], 'true');
  assert.equal(s.dots[0].attributes['aria-current'], undefined);
});
test('automatic rotation wraps with exactly one scheduled change and no live announcements', () => {
  const s = setup(2);
  assert.equal(s.status.attributes['aria-live'], 'off');
  s.tick();
  assert.deepEqual(active(s), [false, true]);
  s.tick();
  assert.deepEqual(active(s), [true, false]);
  assert.equal(s.timers.size, 1);
});
test('hover and mouse focus do not stop autoplay; keyboard focus and background tabs do', () => {
  const s = setup(2);
  s.slider.fire('mouseenter');
  s.slider.fire('focusin', { target: s.next });
  assert.equal(s.timers.size, 1);
  s.next.keyboardFocus = true;
  s.slider.fire('focusin', { target: s.next });
  assert.equal(s.timers.size, 0);
  s.slider.fire('focusout', { relatedTarget: null });
  assert.equal(s.timers.size, 1);
  s.document.hidden = true;
  s.document.fire('visibilitychange');
  assert.equal(s.timers.size, 0);
  s.document.hidden = false;
  s.document.fire('visibilitychange');
  assert.equal(s.timers.size, 1);
});
test('reduced motion disables autoplay and follows changed preferences', () => {
  const s = setup(2, true);
  assert.equal(s.timers.size, 0);
  s.motion.matches = false;
  s.motion.fire('change');
  assert.equal(s.timers.size, 1);
  s.motion.matches = true;
  s.motion.fire('change');
  assert.equal(s.timers.size, 0);
});
test('database interval is used, invalid or missing intervals disable autoplay', () => {
  for (const interval of [2, 5, 15]) assert.equal(setup(2, false, interval).timers.size, 1);
  for (const interval of [0, 1, 16, 31, NaN]) assert.equal(setup(2, false, interval).timers.size, 0);
  assert.equal(source.includes('data-hero-toggle'), false);
});
test('arrow keys work and focus is moved out of a departing slide', () => {
  const s = setup(2);
  s.document.activeElement = s.images[0];
  let prevented = false;
  s.slider.fire('keydown', { key: 'ArrowRight', preventDefault: () => { prevented = true; } });
  assert.equal(prevented, true);
  assert.equal(s.document.activeElement, s.next);
  assert.deepEqual(active(s), [false, true]);
  s.slider.fire('keydown', { key: 'Tab' });
  s.slider.fire('keydown', { key: 'ArrowLeft', altKey: true });
  assert.deepEqual(active(s), [false, true]);
});
test('horizontal touch swipe navigates; vertical scrolling and cancelled gestures do not', () => {
  const s = setup(3);
  const down = { pointerId: 1, pointerType: 'touch', isPrimary: true, clientX: 200, clientY: 50, target: s.images[0] };
  s.slider.fire('pointerdown', down);
  assert.equal(s.timers.size, 0);
  s.slider.fire('pointerup', { pointerId: 1, clientX: 80, clientY: 60 });
  assert.deepEqual(active(s), [false, true, false]);
  let prevented = false;
  s.slider.fire('click', { preventDefault: () => { prevented = true; }, stopImmediatePropagation: () => {} });
  assert.equal(prevented, true);
  s.slider.fire('pointerdown', down);
  s.slider.fire('pointerup', { pointerId: 1, clientX: 180, clientY: 200 });
  assert.deepEqual(active(s), [false, true, false]);
  s.slider.fire('pointerdown', down);
  s.slider.fire('pointercancel');
  assert.equal(s.timers.size, 1);
  s.slider.fire('pointerup', { pointerId: 1, clientX: 80, clientY: 60 });
  assert.deepEqual(active(s), [false, true, false]);
});
test('only current and next images are eagerly requested', () => {
  const s = setup(4);
  assert.deepEqual(s.images.map(image => image.loading), ['eager', 'eager', 'lazy', 'lazy']);
  s.next.fire('click');
  assert.equal(s.images[2].loading, 'eager');
  assert.equal(s.images[3].loading, 'lazy');
});
test('broken pictures are hidden even when only one slide exists', () => {
  const s = setup(1);
  s.images[0].fire('error');
  assert.equal(s.images[0].classes.has('is-unavailable'), true);
});

test('stand time and transition are separate, manual navigation resets a single timer', () => {
  const s = setup(3);
  assert.equal(s.delays.at(-1), 4000);
  s.tick();
  assert.equal(s.delays.at(-1), 4600);
  for (let i = 0; i < 20; i++) s.next.fire('click');
  assert.equal(s.timers.size, 1);
  assert.equal(s.delays.at(-1), 4600);
});
test('reinitialization does not add another timer and leaving the page stops it', () => {
  const s = setup(3);
  s.reinitialize();
  assert.equal(s.timers.size, 1);
  s.window.fire('pagehide');
  assert.equal(s.timers.size, 0);
  s.window.fire('pageshow', { persisted: true });
  assert.equal(s.timers.size, 1);
});
test('persisted settings broadcast immediately restarts with the new seconds value', () => {
  const s = setup(2);
  s.window.fire('storage', { key: 'wallstein.slider.settings', newValue: JSON.stringify({ seconds: 2 }) });
  assert.equal(s.delays.at(-1), 2000);
  assert.equal(s.timers.size, 1);
  s.tick();
  assert.equal(s.delays.at(-1), 2600);
  s.window.fire('storage', { key: 'wallstein.slider.settings', newValue: 'invalid' });
  assert.equal(s.timers.size, 1);
});
