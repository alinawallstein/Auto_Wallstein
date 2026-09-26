(() => {
  const forms = Array.from(document.querySelectorAll('[data-unsaved-form]'));
  const snapshot = form => JSON.stringify(Array.from(new FormData(form), ([key, value]) =>
    [key, value instanceof File ? value.name ? [value.name, value.size, value.lastModified] : '' : value]
  ));
  const states = forms.map(form => ({form, initial: snapshot(form), submitted: false}));
  const dirty = state => !state.submitted &&
    (state.form.hasAttribute('data-unsaved-errors') || snapshot(state.form) !== state.initial);
  states.forEach(state => {
    const status = state.form.querySelector('[data-unsaved-status]');
    const update = () => { if (status) status.textContent = dirty(state) ? 'Ungespeicherte Änderungen' : ''; };
    state.form.addEventListener('input', update);
    state.form.addEventListener('change', update);
    state.form.addEventListener('submit', () => { state.submitted = true; });
  });
  window.addEventListener('beforeunload', event => {
    if (!states.some(dirty)) return;
    event.preventDefault();
    event.returnValue = '';
  });
  window.addEventListener('pageshow', () => states.forEach(state => { state.submitted = false; }));
})();
