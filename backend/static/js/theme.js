(() => {
  const root = document.documentElement;
  const system = window.matchMedia('(prefers-color-scheme: dark)');

  // The site follows the device setting now that the manual switch is removed.
  try { localStorage.removeItem('aw-theme'); } catch (_) {}

  function apply() {
    root.dataset.theme = system.matches ? 'dark' : 'light';
  }

  apply();
  system.addEventListener('change', apply);
})();
