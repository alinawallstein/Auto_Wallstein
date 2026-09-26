const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { runInNewContext } = require('node:vm');
const source = readFileSync(require('node:path').join(__dirname, '../static/js/unsaved-changes.js'), 'utf8');

function setup({ errors = false, file = false } = {}) {
  const formEvents = {};
  const windowEvents = {};
  const status = { textContent: '' };
  let counter = 0;
  class TestFile {
    constructor(name, size, lastModified) { Object.assign(this, { name, size, lastModified }); }
  }
  const form = {
    value: '25990', selectedFile: null,
    querySelector: () => status,
    hasAttribute: () => errors,
    addEventListener: (name, fn) => { formEvents[name] = fn; },
  };
  class TestFormData {
    constructor() {
      this.values = file ? [['images', form.selectedFile || new TestFile('', 0, ++counter)]] : [['price', form.value]];
    }
    [Symbol.iterator]() { return this.values[Symbol.iterator](); }
  }
  runInNewContext(source, {
    document: { querySelectorAll: () => [form] },
    window: { addEventListener: (name, fn) => { windowEvents[name] = fn; } },
    File: TestFile, FormData: TestFormData,
  });
  const warns = () => {
    let prevented = false;
    windowEvents.beforeunload({ preventDefault: () => { prevented = true; } });
    return prevented;
  };
  return { form, formEvents, windowEvents, status, warns, TestFile };
}

test('unchanged values do not warn; changed and restored values are distinguished', () => {
  const state = setup();
  assert.equal(state.warns(), false);
  state.form.value = '30000';
  state.formEvents.input();
  assert.equal(state.status.textContent, 'Ungespeicherte Änderungen');
  assert.equal(state.warns(), true);
  state.form.value = '25990';
  assert.equal(state.warns(), false);
});
test('saving suppresses warning; restoring the page re-enables protection', () => {
  const state = setup();
  state.form.value = '30000';
  state.formEvents.submit();
  assert.equal(state.warns(), false);
  state.windowEvents.pageshow();
  assert.equal(state.warns(), true);
});
test('server validation errors remain protected even before another edit', () => {
  const state = setup({ errors: true });
  assert.equal(state.warns(), true);
  state.formEvents.submit();
  assert.equal(state.warns(), false);
});
test('empty upload fields never warn because of changing empty-file timestamps', () => {
  const state = setup({ file: true });
  assert.equal(state.warns(), false);
  assert.equal(state.warns(), false);
  state.form.selectedFile = new state.TestFile('car.png', 100, 1234);
  assert.equal(state.warns(), true);
  state.form.selectedFile = null;
  assert.equal(state.warns(), false);
});
