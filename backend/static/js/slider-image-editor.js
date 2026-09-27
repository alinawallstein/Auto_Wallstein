(() => {
  const init = () => document.querySelectorAll('[data-slide-editor]').forEach(editor => {
    const form = editor.closest('form');
    const fileInput = form?.querySelector('input[type="file"][name="image"]');
    const prefix = editor.dataset.cropPrefix || 'crop';
    const fields = ['x', 'y', 'width', 'height'].map(name => form?.querySelector(`[name="${prefix}_${name}"]`));
    const scaleField = form?.querySelector(`[name="${editor.dataset.scaleField}"]`);
    const offsetXField = form?.querySelector(`[name="${editor.dataset.offsetXField}"]`);
    const offsetYField = form?.querySelector(`[name="${editor.dataset.offsetYField}"]`);
    const image = editor.querySelector('[data-editor-image]');
    const preview = editor.querySelector('[data-preview-image]');
    const previewFrame = editor.querySelector('[data-editor-preview]');
    const status = editor.querySelector('[data-editor-status]');
    const zoomSlider = editor.querySelector('[data-editor-zoom]');
    const zoomValue = editor.querySelector('[data-zoom-value]');
    if (!form || !fileInput || fields.some(field => !field) || !scaleField || !offsetXField || !offsetYField || !image || !preview || !window.Cropper) return;

    const aspectRatio = Number(editor.dataset.aspect.split(':')[0]) / Number(editor.dataset.aspect.split(':')[1] || 1);
    previewFrame.style.aspectRatio = String(aspectRatio);
    let cropper = null;
    let objectUrl = '';
    let ready = false;
    const saved = fields.map(field => Number(field.value));
    const fullData = () => {
      const width = image.naturalWidth;
      const height = image.naturalHeight;
      const cropWidth = Math.min(width, height * aspectRatio);
      const cropHeight = cropWidth / aspectRatio;
      return { x: (width - cropWidth) / 2, y: (height - cropHeight) / 2, width: cropWidth, height: cropHeight };
    };
    const setImagePosition = (scale, offsetX, offsetY) => {
      scaleField.value = scale.toFixed(2);
      offsetXField.value = offsetX.toFixed(2);
      offsetYField.value = offsetY.toFixed(2);
      zoomSlider.value = String(scale);
      zoomValue.textContent = `${Math.round(scale * 100)} %`;
    };
    const paintPreview = () => {
      if (!cropper || !ready) return;
      const data = cropper.getData();
      fields[0].value = (data.x / image.naturalWidth * 100).toFixed(3);
      fields[1].value = (data.y / image.naturalHeight * 100).toFixed(3);
      fields[2].value = (data.width / image.naturalWidth * 100).toFixed(3);
      fields[3].value = (data.height / image.naturalHeight * 100).toFixed(3);
      const width = 1440;
      const height = Math.round(width / aspectRatio);
      const source = cropper.getCroppedCanvas({ width, height, imageSmoothingEnabled: true, imageSmoothingQuality: 'high' });
      if (!source) return;
      const scale = Math.max(0.6, Math.min(1.3, Number(scaleField.value) || 1));
      const offsetX = Number(offsetXField.value) || 0;
      const offsetY = Number(offsetYField.value) || 0;
      const foregroundWidth = Math.round(width * scale);
      const foregroundHeight = Math.round(height * scale);
      const left = Math.round((width - foregroundWidth) / 2 + width * offsetX / 100);
      const top = Math.round((height - foregroundHeight) / 2 + height * offsetY / 100);
      const needsBackground = left > 0 || top > 0 || left + foregroundWidth < width || top + foregroundHeight < height;
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext('2d');
      if (!context) return;
      if (needsBackground) {
        context.filter = 'blur(34px) brightness(0.62)';
        context.drawImage(source, -34, -34, width + 68, height + 68);
        context.filter = 'none';
      }
      context.drawImage(source, left, top, foregroundWidth, foregroundHeight);
      preview.src = canvas.toDataURL('image/webp', 0.92);
      setImagePosition(scale, offsetX, offsetY);
    };
    const applyScale = value => {
      const scale = Math.max(0.6, Math.min(1.3, Number(value)));
      setImagePosition(scale, Number(offsetXField.value) || 0, Number(offsetYField.value) || 0);
      paintPreview();
    };
    const startCropper = source => {
      ready = false;
      cropper?.destroy();
      image.onload = () => {
        cropper = new Cropper(image, {
          aspectRatio,
          viewMode: 1,
          dragMode: 'crop',
          autoCropArea: 0.8,
          responsive: true,
          background: false,
          guides: true,
          center: true,
          highlight: false,
          movable: false,
          zoomable: false,
          rotatable: false,
          scalable: false,
          cropBoxMovable: true,
          cropBoxResizable: true,
          toggleDragModeOnDblclick: false,
          ready() {
            ready = true;
            const savedRatio = (saved[2] / saved[3]) * image.naturalWidth / image.naturalHeight;
            if (source === editor.dataset.imageUrl && saved[2] > 0 && saved[3] > 0 && Math.abs(savedRatio - aspectRatio) < 0.02) {
              cropper.setData({ x: image.naturalWidth * saved[0] / 100, y: image.naturalHeight * saved[1] / 100,
                width: image.naturalWidth * saved[2] / 100, height: image.naturalHeight * saved[3] / 100 });
            } else {
              cropper.setData(fullData());
              setImagePosition(1, 0, 0);
            }
            paintPreview();
            status.textContent = 'Verschieben Sie den Rahmen oder ziehen Sie eine Ecke. Das Seitenverhältnis bleibt fest.';
          },
          crop: paintPreview,
        });
      };
      image.src = source;
    };

    if (editor.dataset.imageUrl) startCropper(editor.dataset.imageUrl);
    fileInput.addEventListener('change', () => {
      const file = fileInput.files?.[0];
      if (!file) return;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = URL.createObjectURL(file);
      saved.splice(0, saved.length, 0, 0, 0, 0);
      setImagePosition(1, 0, 0);
      startCropper(objectUrl);
    });
    editor.querySelector('[data-editor-reset]')?.addEventListener('click', () => {
      if (!cropper || !ready) return;
      cropper.setData(fullData());
      setImagePosition(1, 0, 0);
      paintPreview();
    });
    zoomSlider.addEventListener('input', () => applyScale(zoomSlider.value));
    editor.querySelectorAll('[data-zoom-step]').forEach(button => button.addEventListener('click', () => {
      const next = Math.max(0.6, Math.min(1.3, Number(zoomSlider.value) + Number(button.dataset.zoomStep)));
      applyScale(next);
    }));
    let drag = null;
    preview.addEventListener('pointerdown', event => {
      if (!ready) return;
      drag = { x: event.clientX, y: event.clientY, offsetX: Number(offsetXField.value) || 0, offsetY: Number(offsetYField.value) || 0 };
      preview.setPointerCapture(event.pointerId);
    });
    preview.addEventListener('pointermove', event => {
      if (!drag) return;
      const box = preview.getBoundingClientRect();
      const offsetX = Math.max(-50, Math.min(50, drag.offsetX + (event.clientX - drag.x) / box.width * 100));
      const offsetY = Math.max(-50, Math.min(50, drag.offsetY + (event.clientY - drag.y) / box.height * 100));
      setImagePosition(Number(scaleField.value) || 1, offsetX, offsetY);
      paintPreview();
    });
    ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(name => preview.addEventListener(name, () => { drag = null; }));
    editor.querySelector('[data-editor-overlay]')?.addEventListener('change', event => previewFrame.classList.toggle('is-overlay-hidden', !event.target.checked));
    form.querySelector('[name="title"]')?.addEventListener('input', event => { editor.querySelector('.slide-editor__copy strong').textContent = event.target.value || 'Mercedes-Benz entdecken'; });
    form.querySelector('[name="subtitle"]')?.addEventListener('input', event => { editor.querySelector('.slide-editor__copy span').textContent = event.target.value || 'Vorschautext im Slider'; });
    window.addEventListener('beforeunload', () => { cropper?.destroy(); if (objectUrl) URL.revokeObjectURL(objectUrl); }, { once: true });
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true }); else init();
})();
