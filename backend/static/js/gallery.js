(() => {
  document.querySelectorAll('[data-gallery]').forEach(gallery => {
    const main = gallery.querySelector('[data-gallery-main]');
    const original = gallery.querySelector('[data-gallery-link]');
    const status = gallery.querySelector('[data-gallery-status]');
    const links = Array.from(gallery.querySelectorAll('[data-gallery-choice]'));
    if (!main || !original || links.length < 2) return;
    const buttons = links.map((link, index) => {
      const picture = link.querySelector('img');
      const button = document.createElement('button');
      button.type = 'button';
      button.setAttribute('aria-label', `Bild ${index + 1} anzeigen: ${picture.alt}`);
      button.setAttribute('aria-pressed', String(index === 0));
      const preview = picture.cloneNode(true);
      preview.alt = '';
      button.append(preview);
      button.addEventListener('click', () => {
        main.src = link.href;
        main.alt = picture.alt;
        original.href = link.href;
        buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
        status.textContent = `Bild ${index + 1} von ${links.length}`;
      });
      link.replaceWith(button);
      return button;
    });
  });
})();
