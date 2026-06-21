/**
 * Helpers globais para formulários.
 *
 * Auto-scroll em erro de submit · ao carregar qualquer página, se houver
 * um banner `.form-err` (resumo de erros do form) ou um `.err` (erro de
 * campo individual), rola suavemente até ele e foca no input adjacente.
 *
 * Regra de UX MPD: nenhum erro de formulário pode passar despercebido —
 * o usuário deve ver o banner imediatamente e ter o cursor pronto para
 * corrigir o primeiro campo problemático.
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', () => {
    const primeiroErro =
      document.querySelector('.form-err') || document.querySelector('.err');
    if (!primeiroErro) return;
    // Aguarda um tick para garantir que layout (sticky, fontes) já se acomodou.
    setTimeout(() => {
      primeiroErro.scrollIntoView({ behavior: 'smooth', block: 'center' });
      const campo = primeiroErro
        .closest('.field, .formset-row, .cp-field')
        ?.querySelector('input, select, textarea');
      if (campo && typeof campo.focus === 'function') {
        campo.focus({ preventScroll: true });
      }
    }, 80);
  });
})();
