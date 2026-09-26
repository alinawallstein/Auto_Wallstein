(() => {
  const saved = document.querySelector('[data-slider-saved-interval]');
  if (!saved) return;
  // Notify open homepage tabs of the persisted value, never the unsaved input.
  try {
    localStorage.setItem('wallstein.slider.settings', JSON.stringify({
      seconds: Number(saved.dataset.sliderSavedInterval), savedAt: Date.now(),
    }));
  } catch { /* Storage may be disabled; a page reload still reads the database. */ }
})();
