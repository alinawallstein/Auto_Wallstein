(() => {
  const widget = document.querySelector('[data-accessibility-widget]');
  if (!widget) return;

  const root = document.documentElement;
  const trigger = widget.querySelector('[data-a11y-trigger]');
  const panel = widget.querySelector('.aw-accessibility__panel');
  const sizeLabel = widget.querySelector('[data-a11y-text-size]');
  const storageKey = 'wallstein.a11y.settings';
  const defaults = { fontScale: 1, highContrast: false, highlightLinks: false, reduceMotion: false };
  let settings = { ...defaults };

  try {
    const stored = JSON.parse(localStorage.getItem(storageKey) || '{}');
    const fontScale = Number(stored.fontScale);
    settings = {
      fontScale: Number.isFinite(fontScale) ? Math.max(.8, Math.min(1.4, fontScale)) : defaults.fontScale,
      highContrast: stored.highContrast === true,
      highlightLinks: stored.highlightLinks === true,
      reduceMotion: stored.reduceMotion === true,
    };
  } catch { /* Storage may be disabled; controls still work for this page. */ }

  const setPressed = (name, pressed) => {
    const button = widget.querySelector(`[data-a11y-action="${name}"]`);
    button?.setAttribute('aria-pressed', String(pressed));
  };

  function applySettings(save = true) {
    root.style.setProperty('--aw-font-scale', String(settings.fontScale));
    root.classList.toggle('aw-high-contrast', settings.highContrast);
    root.classList.toggle('aw-highlight-links', settings.highlightLinks);
    root.classList.toggle('user-reduced-motion', settings.reduceMotion);
    sizeLabel.textContent = `${Math.round(settings.fontScale * 100)} %`;
    setPressed('contrast', settings.highContrast);
    setPressed('links', settings.highlightLinks);
    setPressed('motion', settings.reduceMotion);
    if (save) {
      try { localStorage.setItem(storageKey, JSON.stringify(settings)); }
      catch { /* Keep the current-page preference when storage is unavailable. */ }
    }
    window.dispatchEvent(new CustomEvent('wallstein:motion-preference', {
      detail: { reduced: settings.reduceMotion },
    }));
  }

  function setOpen(open, restoreFocus = false) {
    panel.hidden = !open;
    trigger.setAttribute('aria-expanded', String(open));
    trigger.setAttribute('aria-label', open ? 'Barrierefreiheit schließen' : 'Barrierefreiheit öffnen');
    if (!open && restoreFocus) trigger.focus();
  }

  trigger.addEventListener('click', () => setOpen(panel.hidden));
  widget.addEventListener('click', event => {
    const action = event.target.closest('[data-a11y-action]')?.dataset.a11yAction;
    if (!action) return;
    if (action === 'text-larger') settings.fontScale = Math.min(1.4, Math.round((settings.fontScale + .1) * 10) / 10);
    if (action === 'text-smaller') settings.fontScale = Math.max(.8, Math.round((settings.fontScale - .1) * 10) / 10);
    if (action === 'contrast') settings.highContrast = !settings.highContrast;
    if (action === 'links') settings.highlightLinks = !settings.highlightLinks;
    if (action === 'motion') settings.reduceMotion = !settings.reduceMotion;
    if (action === 'reset') settings = { ...defaults };
    applySettings();
  });

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !panel.hidden) setOpen(false, true);
  });
  document.addEventListener('pointerdown', event => {
    if (!panel.hidden && !widget.contains(event.target)) setOpen(false, widget.contains(document.activeElement));
  });

  applySettings(false);
})();
