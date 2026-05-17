/**
 * Autocomplete server-side para selects de Pessoa e Entidade.
 *
 * Marca-se um <select> com `data-autocomplete="pessoa"` ou `"entidade"` e o
 * script transforma em combobox pesquisável que consulta /pessoas/buscar.json
 * ou /entidades/buscar.json. O <select> original fica oculto mas presente no
 * DOM — submit do form continua enviando o `name=pessoa`/`name=entidade` com
 * o ID escolhido. Fallback: sem JS, o select normal continua funcional.
 *
 * Reinicializar para novos selects (ex.: formset 'add row' dinâmico):
 *   window.MPDAutocomplete.init(elementoPai)
 */
(function () {
  'use strict';

  const ENDPOINTS = {
    pessoa: '/pessoas/buscar.json',
    entidade: '/entidades/buscar.json',
  };

  function montar(selectOriginal) {
    const tipo = selectOriginal.dataset.autocomplete;
    const endpoint = ENDPOINTS[tipo];
    if (!endpoint) return;

    const wrapper = document.createElement('div');
    wrapper.className = 'autocomplete-wrapper relative';
    selectOriginal.parentNode.insertBefore(wrapper, selectOriginal);

    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Digite para buscar...';
    input.autocomplete = 'off';
    input.className = selectOriginal.className;
    wrapper.appendChild(input);

    const dropdown = document.createElement('div');
    dropdown.className =
      'autocomplete-dropdown absolute z-30 hidden mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-60 overflow-y-auto';
    wrapper.appendChild(dropdown);

    // Esconde o select original mas o mantém no DOM (form submit pega o value)
    selectOriginal.style.display = 'none';
    wrapper.appendChild(selectOriginal);

    // Estado pré-existente: form de edição com valor selecionado
    if (selectOriginal.value) {
      const opt = selectOriginal.options[selectOriginal.selectedIndex];
      if (opt && opt.value) input.value = opt.text.trim();
    }

    let timer = null;

    function buscar(q) {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        try {
          const resp = await fetch(endpoint + '?q=' + encodeURIComponent(q));
          if (!resp.ok) throw new Error('HTTP ' + resp.status);
          const data = await resp.json();
          renderResultados(data.resultados || []);
        } catch (e) {
          dropdown.innerHTML =
            '<div class="px-3 py-2 text-sm text-red-600">Erro ao buscar.</div>';
          dropdown.classList.remove('hidden');
        }
      }, 200);
    }

    function escape(s) {
      return String(s).replace(/[&<>"']/g, (c) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
      })[c]);
    }

    function renderResultados(lista) {
      if (!lista.length) {
        dropdown.innerHTML =
          '<div class="px-3 py-2 text-sm text-slate-500">Nenhum resultado. Verifique se está cadastrado.</div>';
      } else {
        dropdown.innerHTML = lista
          .map(
            (r) => `
              <div class="autocomplete-item px-3 py-2 cursor-pointer hover:bg-slate-50 border-b border-slate-100 last:border-0"
                   data-id="${escape(r.id)}" data-label="${escape(r.label)}">
                <div class="text-sm text-slate-900">${escape(r.label)}</div>
                ${r.secundario ? `<div class="text-xs text-slate-500">${escape(r.secundario)}</div>` : ''}
              </div>`,
          )
          .join('');
        dropdown.querySelectorAll('.autocomplete-item').forEach((item) => {
          item.addEventListener('click', () => {
            const id = item.dataset.id;
            const label = item.dataset.label;
            // Garante que o select tenha a option correspondente para passar
            // pela validação do ModelChoiceField (que itera options).
            let optExistente = selectOriginal.querySelector(`option[value="${id}"]`);
            if (!optExistente) {
              optExistente = document.createElement('option');
              optExistente.value = id;
              optExistente.text = label;
              selectOriginal.appendChild(optExistente);
            }
            selectOriginal.value = id;
            input.value = label;
            dropdown.classList.add('hidden');
            selectOriginal.dispatchEvent(new Event('change', { bubbles: true }));
          });
        });
      }
      dropdown.classList.remove('hidden');
    }

    input.addEventListener('input', () => {
      // Edição limpa a seleção atual
      selectOriginal.value = '';
      buscar(input.value);
    });
    input.addEventListener('focus', () => buscar(input.value));
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        dropdown.classList.add('hidden');
      }
    });
    document.addEventListener('click', (e) => {
      if (!wrapper.contains(e.target)) dropdown.classList.add('hidden');
    });
  }

  function init(root) {
    (root || document)
      .querySelectorAll('select[data-autocomplete]:not([data-autocomplete-initialized])')
      .forEach((s) => {
        s.setAttribute('data-autocomplete-initialized', 'true');
        montar(s);
      });
  }

  document.addEventListener('DOMContentLoaded', () => init());
  window.MPDAutocomplete = { init };
})();


/**
 * Toggle do campo "papel_outro" nos formsets de DemandaPessoa/DemandaEntidade.
 * O input só aparece quando papel === 'outro'. Cada linha tem class
 * `papel-row` e contém o select e o wrap `.papel-outro-wrap`.
 */
(function () {
  'use strict';

  function bindPapelToggle(root) {
    (root || document).querySelectorAll('.papel-row').forEach((row) => {
      const select = row.querySelector('select[name$="papel"]');
      const outroWrap = row.querySelector('.papel-outro-wrap');
      if (!select || !outroWrap) return;
      if (select.dataset.papelToggleInitialized) return;
      select.dataset.papelToggleInitialized = 'true';

      function aplicar() {
        outroWrap.style.display = select.value === 'outro' ? '' : 'none';
      }
      select.addEventListener('change', aplicar);
      aplicar();
    });
  }

  document.addEventListener('DOMContentLoaded', () => bindPapelToggle());
  window.MPDPapelToggle = { init: bindPapelToggle };
})();

