(() => {
  const AUTOPLAY_DELAY = 6000;
  const MIN_SWIPE_DISTANCE = 50;

  document.querySelectorAll('[data-hero-slider]').forEach(slider => {
    const slides = Array.from(slider.querySelectorAll('[data-hero-slide]'));
    slider.querySelectorAll('[data-hero-image]').forEach(image => {
      const markUnavailable = () => { image.classList.add('is-unavailable'); };
      image.addEventListener('error', markUnavailable);
      if (image.complete && image.naturalWidth === 0) markUnavailable();
    });
    const controls = slider.querySelector('[data-hero-controls]');
    if (slides.length < 2 || !controls) return;
    const previous = controls.querySelector('[data-hero-previous]');
    const next = controls.querySelector('[data-hero-next]');
    const toggle = controls.querySelector('[data-hero-toggle]');
    const status = controls.querySelector('[data-hero-status]');
    const dots = Array.from(controls.querySelectorAll('[data-hero-dot]'));
    if (!previous || !next || !toggle || !status || dots.length !== slides.length) return;

    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let paused = motion.matches;
    let hovered = false;
    let focused = false;
    let pointer = null;
    let suppressClick = false;
    let timer = null;
    let index = 0;

    function schedule() {
      window.clearTimeout(timer);
      timer = null;
      const rotating = !paused && !hovered && !focused && !pointer && !document.hidden;
      status.setAttribute('aria-live', rotating ? 'off' : 'polite');
      toggle.textContent = paused ? 'Abspielen' : 'Pause';
      toggle.setAttribute('aria-label', paused ? 'Automatischen Bildwechsel starten' : 'Automatischen Bildwechsel pausieren');
      if (rotating) timer = window.setTimeout(() => show(index + 1), AUTOPLAY_DELAY);
    }
    function show(position) {
      const target = (position + slides.length) % slides.length;
      if (target !== index && slides[index].contains(document.activeElement)) toggle.focus();
      index = target;
      slides.forEach((slide, current) => {
        const active = current === index;
        slide.classList.toggle('is-active', active);
        slide.inert = !active;
        slide.setAttribute('aria-hidden', String(!active));
        if (active) dots[current].setAttribute('aria-current', 'true');
        else dots[current].removeAttribute('aria-current');
      });
      // Load the current and next picture, leaving the remaining uploads lazy.
      [index, (index + 1) % slides.length].forEach(position => {
        const image = slides[position].querySelector('[data-hero-image]');
        if (image) image.loading = 'eager';
      });
      status.textContent = `Slide ${index + 1} von ${slides.length}`;
      schedule();
    }
    previous.addEventListener('click', () => show(index - 1));
    next.addEventListener('click', () => show(index + 1));
    dots.forEach((dot, position) => dot.addEventListener('click', () => show(position)));
    toggle.addEventListener('click', () => { paused = !paused; schedule(); });
    slider.addEventListener('keydown', event => {
      if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      show(index + (event.key === 'ArrowRight' ? 1 : -1));
    });
    slider.addEventListener('mouseenter', () => { hovered = true; schedule(); });
    slider.addEventListener('mouseleave', () => { hovered = false; schedule(); });
    slider.addEventListener('focusin', () => { focused = true; schedule(); });
    slider.addEventListener('focusout', event => {
      focused = slider.contains(event.relatedTarget);
      schedule();
    });
    slider.addEventListener('pointerdown', event => {
      suppressClick = false;
      if (event.pointerType === 'mouse' || !event.isPrimary || controls.contains(event.target)) return;
      pointer = { id: event.pointerId, x: event.clientX, y: event.clientY };
      schedule();
    });
    slider.addEventListener('pointerup', event => {
      if (!pointer || pointer.id !== event.pointerId) return;
      const dx = event.clientX - pointer.x;
      const dy = event.clientY - pointer.y;
      pointer = null;
      if (Math.abs(dx) >= MIN_SWIPE_DISTANCE && Math.abs(dx) > Math.abs(dy)) {
        suppressClick = true;
        show(index + (dx < 0 ? 1 : -1));
      } else schedule();
    });
    const cancelPointer = () => { pointer = null; schedule(); };
    slider.addEventListener('pointercancel', cancelPointer);
    slider.addEventListener('pointerleave', cancelPointer);
    slider.addEventListener('click', event => {
      if (!suppressClick) return;
      suppressClick = false;
      event.preventDefault();
      event.stopImmediatePropagation();
    }, true);
    document.addEventListener('visibilitychange', () => {
      pointer = null;
      schedule();
    });
    motion.addEventListener('change', event => {
      if (event.matches) paused = true;
      schedule();
    });
    slider.classList.add('is-enhanced');
    // Stacked grid panels reserve room for the longest copy without making it focusable.
    slides.forEach(slide => { slide.hidden = false; });
    controls.hidden = false;
    show(0);
  });
})();
