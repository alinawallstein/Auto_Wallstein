(() => {
  const focusSummary = () => document.querySelector('[data-error-summary]')?.focus();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', focusSummary, { once: true });
  else focusSummary();
})();
