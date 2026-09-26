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
  addEventListener(name, fn) { this.events[name] = fn; }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
  contains(target) { return this === target || this.children.some(child => child.contains(target)); }
  querySelector(selector) { return this.selectors?.[selector] || null; }
  querySelectorAll(selector) { return this.groups?.[selector] || []; }
  fire(name, event = {}) { this.events[name]?.(event); }
}
function setup(count, reducedMotion = false) {
  const timers = new Map();
  let timerId = 0;
  const images = Array.from({ length: count }, () => Object.assign(new Element(), { complete: true, naturalWidth: 1600, loading: 'lazy' }));
  const slides = images.map(image => Object.assign(new Element(), {
    hidden: true, selectors: { '[data-hero-image]': image }, children: [image],
  }));
  const controls = Object.assign(new Element(), { hidden: true });
  const previous = new Element();
  const next = new Element();
  const toggle = new Element();
  const status = new Element();
  const dots = slides.map(() => new Element());
  controls.selectors = { '[data-hero-previous]': previous, '[data-hero-next]': next, '[data-hero-toggle]': toggle, '[data-hero-status]': status };
  controls.groups = { '[data-hero-dot]': dots };
  controls.children = [previous, next, toggle, status, ...dots];
  const slider = Object.assign(new Element(), {
    children: [controls, ...slides],
    selectors: { '[data-hero-controls]': count > 1 ? controls : null },
    groups: { '[data-hero-slide]': slides, '[data-hero-image]': images },
  });
  const document = Object.assign(new Element(), { hidden: false, activeElement: null, groups: { '[data-hero-slider]': [slider] } });
  toggle.focus = () => { document.activeElement = toggle; slider.fire('focusin'); };
  const motion = Object.assign(new Element(), { matches: reducedMotion });
  const window = {
    matchMedia: () => motion,
    setTimeout: (fn, delay) => { assert.equal(delay, 6000); timers.set(++timerId, fn); return timerId; },
    clearTimeout: id => timers.delete(id),
  };
  runInNewContext(source, { document, window });
  const tick = () => { const [id, fn] = timers.entries().next().value; timers.delete(id); fn(); };
  return { slider, slides, images, previous, next, toggle, status, dots, controls, timers, tick, document, motion };
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
test('explicit pause survives interactions and manual navigation', () => {
  const s = setup(2);
  s.toggle.fire('click');
  s.slider.fire('mouseenter');
  s.slider.fire('mouseleave');
  s.document.fire('visibilitychange');
  s.next.fire('click');
  assert.equal(s.timers.size, 0);
  assert.equal(s.status.attributes['aria-live'], 'polite');
  s.toggle.fire('click');
  assert.equal(s.timers.size, 1);
});
test('hover, focus and background tabs pause without accumulating timers', () => {
  const s = setup(2);
  s.slider.fire('mouseenter');
  assert.equal(s.timers.size, 0);
  s.slider.fire('focusin');
  s.slider.fire('mouseleave');
  assert.equal(s.timers.size, 0);
  s.slider.fire('focusout', { relatedTarget: s.toggle });
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
test('reduced motion starts paused and responds to changed preferences', () => {
  const s = setup(2, true);
  assert.equal(s.timers.size, 0);
  s.toggle.fire('click');
  assert.equal(s.timers.size, 1);
  s.motion.fire('change', { matches: true });
  assert.equal(s.timers.size, 0);
});
test('arrow keys work and focus is moved out of a departing slide', () => {
  const s = setup(2);
  s.document.activeElement = s.images[0];
  let prevented = false;
  s.slider.fire('keydown', { key: 'ArrowRight', preventDefault: () => { prevented = true; } });
  assert.equal(prevented, true);
  assert.equal(s.document.activeElement, s.toggle);
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
