(() => {
  const success = document.getElementById('contact-success');
  if (success) {
    success.focus();
    return;
  }

  const form = document.querySelector('.contact-form');
  const button = form?.querySelector('button[type="submit"]');
  if (!button) return;
  const label = button.textContent;
  form.addEventListener('submit', () => {
    button.disabled = true;
    button.textContent = 'Anfrage wird gesendet …';
    form.setAttribute('aria-busy', 'true');
  });
  window.addEventListener('pageshow', () => {
    button.disabled = false;
    button.textContent = label;
    form.removeAttribute('aria-busy');
  });
})();
