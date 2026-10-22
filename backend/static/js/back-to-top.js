(() => {
  const button = document.querySelector('.back-to-top');
  if (!button) return;
  const brand = document.querySelector('.site-brand');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  function update() {
    const visible = window.scrollY > 320;
    if (!visible && document.activeElement === button) brand?.focus({ preventScroll: true });
    button.hidden = !visible;
  }

  button.addEventListener('click', () => {
    brand?.focus({ preventScroll: true });
    const reduced = reducedMotion.matches || document.documentElement.classList.contains('user-reduced-motion');
    window.scrollTo({ top: 0, behavior: reduced ? 'instant' : 'smooth' });
  });
  window.addEventListener('scroll', update, { passive: true });
  window.addEventListener('pageshow', update);
  update();
})();
