/**
 * Seletor de cor: paleta de swatches + input hex + color picker nativo + prévia.
 *
 * Inicialização automática: busca o primeiro formulário da página que contenha
 * um input[name=cor]. Funciona para tag-form e tema-form sem configuração extra.
 *
 * CSS dos elementos: components.css (.cor-swatch, .cor-swatch.sel, etc.)
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', () => {
    // Encontra o formulário que contém o campo "cor" (tag-form ou tema-form).
    const form = document.querySelector('form input[name=cor]')?.closest('form');
    if (!form) return;

    const corInput    = form.querySelector('input[name=cor]');
    const corPicker   = document.getElementById('cor-picker');
    const corPreview  = document.getElementById('cor-preview');
    const nomeInput   = form.querySelector('input[name=nome]');
    const swatches    = form.querySelectorAll('.cor-swatch');
    const previewDefault = corPreview?.dataset.previewDefault || 'item';

    function hexValido(v) { return /^#[0-9a-fA-F]{6}$/.test((v || '').trim()); }

    function aplicarCor(hex) {
      if (!hexValido(hex)) {
        if (corPreview) {
          corPreview.style.background = 'var(--ink-100)';
          corPreview.style.color = 'var(--ink-soft)';
        }
        swatches.forEach(s => s.classList.remove('sel'));
        return;
      }
      if (corPreview) {
        corPreview.style.background = `color-mix(in srgb, ${hex} 14%, white)`;
        corPreview.style.color = `color-mix(in srgb, ${hex} 75%, black)`;
      }
      if (corPicker) corPicker.value = hex;
      swatches.forEach(s => {
        s.classList.toggle('sel', s.dataset.cor.toLowerCase() === hex.toLowerCase());
      });
    }

    function atualizarPreviewTexto() {
      if (corPreview && nomeInput) {
        corPreview.textContent = (nomeInput.value || previewDefault).trim() || previewDefault;
      }
    }

    swatches.forEach(s => {
      s.addEventListener('click', () => {
        corInput.value = s.dataset.cor;
        aplicarCor(s.dataset.cor);
      });
    });

    document.getElementById('cor-personalizar-btn')?.addEventListener('click', () => corPicker?.click());
    corInput?.addEventListener('input', () => aplicarCor(corInput.value));
    corPicker?.addEventListener('input', () => {
      corInput.value = corPicker.value;
      aplicarCor(corPicker.value);
    });
    nomeInput?.addEventListener('input', atualizarPreviewTexto);

    // Estado inicial
    atualizarPreviewTexto();
    if (corInput?.value) aplicarCor(corInput.value);
  });
})();
