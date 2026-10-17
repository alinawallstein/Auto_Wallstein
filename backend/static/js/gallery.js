(() => {
  document.querySelectorAll('[data-gallery]').forEach(gallery => {
    const main = gallery.querySelector('[data-gallery-main]');
    const original = gallery.querySelector('[data-gallery-link]');
    const stage = gallery.querySelector('[data-gallery-stage]');
    const status = gallery.querySelector('[data-gallery-status]');
    const previous = gallery.querySelector('[data-gallery-previous]');
    const next = gallery.querySelector('[data-gallery-next]');
    const items = Array.from(gallery.querySelectorAll('[data-gallery-choice]'));
    if (!main || !original || !stage || !previous || !next || items.length < 2) return;
    let index = 0;
    function show(target) {
      index = (target + items.length) % items.length;
      main.src = items[index].href;
      main.alt = items[index].dataset.alt || '';
      original.href = items[index].href;
      status.textContent = `Bild ${index + 1} von ${items.length}`;
    }
    previous.hidden = next.hidden = false;
    previous.addEventListener('click', () => show(index - 1));
    next.addEventListener('click', () => show(index + 1));
    gallery.addEventListener('keydown', event => {
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
        event.preventDefault();
        show(index + (event.key === 'ArrowRight' ? 1 : -1));
      }
    });
    let touch = null;
    let swiped = false;
    stage.addEventListener('touchstart', event => {
      swiped = false;
      touch = event.touches.length === 1 ? { x: event.touches[0].clientX, y: event.touches[0].clientY } : null;
    }, { passive: true });
    stage.addEventListener('touchend', event => {
      if (!touch || !event.changedTouches.length) return;
      const dx = event.changedTouches[0].clientX - touch.x;
      const dy = event.changedTouches[0].clientY - touch.y;
      touch = null;
      if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        swiped = true;
        show(index + (dx < 0 ? 1 : -1));
      }
    }, { passive: true });
    stage.addEventListener('touchcancel', () => { touch = null; swiped = false; });
    original.addEventListener('click', event => {
      if (swiped) { event.preventDefault(); swiped = false; }
    });
  });
})();
