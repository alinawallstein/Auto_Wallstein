(() => {
  const toggle = document.querySelector('.site-menu-toggle');
  const menu = document.getElementById('site-menu');
  if (!toggle || !menu) return;
  const mobile = window.matchMedia('(max-width: 60rem)');
  function closeMenu() {
    toggle.setAttribute('aria-expanded', 'false');
    menu.hidden = mobile.matches;
  }
  function updateLayout() {
    const focused = document.activeElement;
    toggle.hidden = !mobile.matches;
    closeMenu();
    if (mobile.matches && menu.contains(focused)) toggle.focus();
    if (!mobile.matches && focused === toggle) menu.querySelector('a').focus();
  }
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(open));
    menu.hidden = !open;
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && mobile.matches && !menu.hidden) {
      closeMenu();
      toggle.focus();
    }
  });
  menu.addEventListener('click', event => {
    if (event.target.closest('a') && mobile.matches) closeMenu();
  });
  mobile.addEventListener('change', updateLayout);
  updateLayout();
})();
