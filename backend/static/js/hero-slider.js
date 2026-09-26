(() => {
  const MIN_SWIPE_DISTANCE = 50;
  const secondsToMilliseconds = value => Number(value) * 1000;

  document.querySelectorAll('[data-hero-slider]').forEach(slider => {
    if (slider.dataset.heroInitialized) return;
    slider.dataset.heroInitialized = 'true';
    const slides = Array.from(slider.querySelectorAll('[data-hero-slide]'));
    slider.querySelectorAll('[data-hero-image]').forEach(image => {
      const unavailable = () => image.classList.add('is-unavailable');
      image.addEventListener('error', unavailable);
      if (image.complete && !image.naturalWidth) unavailable();
    });
    const controls = slider.querySelector('[data-hero-controls]');
    if (slides.length < 2 || !controls) return;
    const previous = controls.querySelector('[data-hero-previous]');
    const next = controls.querySelector('[data-hero-next]');
    const status = controls.querySelector('[data-hero-status]');
    const dots = Array.from(controls.querySelectorAll('[data-hero-dot]'));
    if (!previous || !next || !status || dots.length !== slides.length) return;

    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let interval = secondsToMilliseconds(slider.dataset.interval);
    let index = 0;
    let timer = null;
    let keyboardFocus = false;
    let pointer = null;
    let suppressClick = false;

    function stop() {
      window.clearTimeout(timer);
      timer = null;
    }
    function schedule(transition = 0) {
      stop();
      const running = Number.isFinite(interval) && interval >= 2000 && interval <= 15000 &&
        !motion.matches && !document.hidden && !keyboardFocus && !pointer;
      status.setAttribute('aria-live', running ? 'off' : 'polite');
      if (running) timer = window.setTimeout(() => show(index + 1), interval + transition);
    }
    function show(position) {
      const target = (position + slides.length) % slides.length;
      if (target !== index && slides[index].contains(document.activeElement)) next.focus();
      index = target;
      slides.forEach((slide, current) => {
        const active = current === index;
        slide.classList.toggle('is-active', active);
        slide.inert = !active;
        slide.setAttribute('aria-hidden', String(!active));
        if (active) dots[current].setAttribute('aria-current', 'true');
        else dots[current].removeAttribute('aria-current');
      });
      [index, (index + 1) % slides.length].forEach(position => {
        const image = slides[position].querySelector('[data-hero-image]');
        if (image) image.loading = 'eager';
      });
      status.textContent = `Slide ${index + 1} von ${slides.length}`;
      // CSS owns animation duration. The database interval is the still time after the fade.
      const fade = parseFloat(window.getComputedStyle(slides[index]).transitionDuration) || 0;
      schedule(secondsToMilliseconds(fade));
    }
    previous.addEventListener('click', () => show(index - 1));
    next.addEventListener('click', () => show(index + 1));
    dots.forEach((dot, position) => dot.addEventListener('click', () => show(position)));
    slider.addEventListener('keydown', event => {
      if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      show(index + (event.key === 'ArrowRight' ? 1 : -1));
    });
    slider.addEventListener('focusin', event => {
      keyboardFocus = event.target.matches(':focus-visible');
      if (keyboardFocus) schedule();
    });
    slider.addEventListener('focusout', event => {
      if (slider.contains(event.relatedTarget)) return;
      keyboardFocus = false;
      schedule();
    });
    slider.addEventListener('pointerdown', event => {
      if (keyboardFocus) { keyboardFocus = false; schedule(); }
      suppressClick = false;
      if (event.pointerType === 'mouse' || !event.isPrimary || controls.contains(event.target)) return;
      pointer = { id: event.pointerId, x: event.clientX, y: event.clientY };
      slider.setPointerCapture(event.pointerId);
      stop();
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
    slider.addEventListener('pointercancel', () => {
      if (!pointer) return;
      pointer = null;
      schedule();
    });
    slider.addEventListener('click', event => {
      if (!suppressClick) return;
      suppressClick = false;
      event.preventDefault();
      event.stopImmediatePropagation();
    }, true);
    document.addEventListener('visibilitychange', () => { pointer = null; schedule(); });
    motion.addEventListener('change', () => schedule());
    window.addEventListener('pagehide', stop);
    window.addEventListener('pageshow', event => { if (event.persisted) schedule(); });
    window.addEventListener('storage', event => {
      if (event.key !== 'wallstein.slider.settings' || !event.newValue) return;
      try {
        const value = secondsToMilliseconds(JSON.parse(event.newValue).seconds);
        if (!Number.isFinite(value) || value < 2000 || value > 15000 || value === interval) return;
        interval = value;
        schedule();
      } catch { /* Ignore malformed notifications; the rendered database value remains valid. */ }
    });
    slider.classList.add('is-enhanced');
    slides.forEach(slide => { slide.hidden = false; });
    controls.hidden = false;
    show(0);
    schedule();
  });
})();
