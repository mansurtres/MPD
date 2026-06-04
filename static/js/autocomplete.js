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
  const ENDPOINTS_CRIAR = {
    pessoa: '/pessoas/criar.json',
    entidade: '/entidades/criar.json',
  };
  const ROTULOS = { pessoa: 'pessoa', entidade: 'entidade' };

  // Select que disparou o drawer de criação rápida — quando o drawer salva,
  // injetamos o resultado de volta no select certo (cada autocomplete tem o
  // próprio <select> oculto que recebe o id escolhido).
  let selectAlvoDoDrawer = null;

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
      const q = input.value.trim();
      const drawerExiste = !!document.getElementById('drawer-criar-parte');
      const ofereceCriar = drawerExiste && q.length >= 2;
      const rotulo = ROTULOS[tipo] || tipo;

      if (!lista.length) {
        dropdown.innerHTML =
          '<div class="px-3 py-2 text-sm text-slate-500">Nenhum resultado.</div>';
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
      }

      if (ofereceCriar) {
        const div = document.createElement('div');
        div.className = 'autocomplete-item-criar';
        div.dataset.criar = q;
        div.innerHTML =
          '+ cadastrar ' + escape(rotulo) + ' <span class="nome">"' + escape(q) + '"</span>';
        dropdown.appendChild(div);
        div.addEventListener('click', () => {
          dropdown.classList.add('hidden');
          abrirDrawerCriar(tipo, q, selectOriginal, input);
        });
      }

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

  // Drawer de criação rápida · acionado pelo botão "+ cadastrar ..." do
  // dropdown. Reaproveita o template `_drawer_criar_parte.html` (incluído
  // em form.html). Submit faz POST AJAX e injeta o resultado no select que
  // disparou a abertura.
  let inputAlvoDoDrawer = null;

  function abrirDrawerCriar(tipo, nomePrefill, selectOriginal, inputBusca) {
    const drawer = document.getElementById('drawer-criar-parte');
    if (!drawer) return;
    selectAlvoDoDrawer = selectOriginal;
    inputAlvoDoDrawer = inputBusca;

    const form = drawer.querySelector('[data-cp-form]');
    form.dataset.cpTipo = tipo;
    form.querySelector('input[name=nome]').value = nomePrefill;
    form.querySelector('input[name=telefone]').value = '';
    form.querySelector('input[name=email]').value = '';
    form.querySelector('select[name=tipo]').value = 'associacao';
    drawer.querySelector('[data-cp-tipo-label]').textContent = ROTULOS[tipo] || tipo;
    drawer.querySelector('[data-cp-helper-pessoa]').hidden = tipo !== 'pessoa';
    drawer.querySelector('[data-cp-helper-entidade]').hidden = tipo !== 'entidade';
    drawer.querySelector('[data-cp-pessoa]').hidden = tipo !== 'pessoa';
    drawer.querySelector('[data-cp-entidade]').hidden = tipo !== 'entidade';
    drawer.querySelector('[data-cp-err]').hidden = true;
    drawer.classList.remove('hidden');
    drawer.setAttribute('aria-hidden', 'false');
    // Foco no campo nome (já preenchido — o usuário pode ajustar ou pular)
    setTimeout(() => form.querySelector('input[name=nome]').focus(), 50);
  }

  function fecharDrawerCriar() {
    const drawer = document.getElementById('drawer-criar-parte');
    if (!drawer) return;
    drawer.classList.add('hidden');
    drawer.setAttribute('aria-hidden', 'true');
    selectAlvoDoDrawer = null;
    inputAlvoDoDrawer = null;
  }

  async function submeterDrawerCriar(e) {
    e.preventDefault();
    const drawer = document.getElementById('drawer-criar-parte');
    const form = drawer.querySelector('[data-cp-form]');
    const tipo = form.dataset.cpTipo;
    const endpoint = ENDPOINTS_CRIAR[tipo];
    if (!endpoint || !selectAlvoDoDrawer) return;

    const errBox = drawer.querySelector('[data-cp-err]');
    errBox.hidden = true;

    const fd = new FormData(form);
    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        body: fd,
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      const data = await resp.json();
      if (!resp.ok) {
        errBox.textContent = data.erro || 'Erro ao criar.';
        errBox.hidden = false;
        return;
      }
      // Injeta no select e seleciona
      let opt = selectAlvoDoDrawer.querySelector(`option[value="${data.id}"]`);
      if (!opt) {
        opt = document.createElement('option');
        opt.value = data.id;
        opt.text = data.label;
        selectAlvoDoDrawer.appendChild(opt);
      }
      selectAlvoDoDrawer.value = data.id;
      if (inputAlvoDoDrawer) inputAlvoDoDrawer.value = data.label;
      selectAlvoDoDrawer.dispatchEvent(new Event('change', { bubbles: true }));
      fecharDrawerCriar();
    } catch (err) {
      errBox.textContent = 'Erro de rede ao criar. Tente novamente.';
      errBox.hidden = false;
    }
  }

  function ativarDrawerCriar() {
    const drawer = document.getElementById('drawer-criar-parte');
    if (!drawer) return;
    drawer.querySelectorAll('[data-cp-close]').forEach((b) =>
      b.addEventListener('click', fecharDrawerCriar),
    );
    drawer.querySelector('[data-cp-form]').addEventListener('submit', submeterDrawerCriar);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !drawer.classList.contains('hidden')) fecharDrawerCriar();
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    init();
    ativarDrawerCriar();
  });
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

