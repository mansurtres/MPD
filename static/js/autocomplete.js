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
  // Drawer agora submete pro endpoint real de criação (PessoaCreateView /
  // EntidadeCreateView), que detecta X-Requested-With e responde JSON.
  // Garante coerência absoluta com o form completo — mesmas validações,
  // mesmos signals, mesmas regras de negócio.
  const ENDPOINTS_CRIAR = {
    pessoa: '/pessoas/nova/',
    entidade: '/entidades/nova/',
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
    form.reset();

    // Pré-preenche o nome com o que o usuário digitou. Pra pessoa, tenta
    // dividir no primeiro espaço (primeiro token = nome, resto = sobrenome).
    if (tipo === 'pessoa') {
      const partes = (nomePrefill || '').trim().split(/\s+/);
      form.querySelector('input[name=nome]').value = partes[0] || '';
      form.querySelector('input[name=sobrenome]').value = partes.slice(1).join(' ');
    } else {
      form.querySelector('input[name=ent_nome]').value = nomePrefill || '';
    }

    drawer.querySelector('[data-cp-tipo-label]').textContent = ROTULOS[tipo] || tipo;
    const blocoPessoa = drawer.querySelector('[data-cp-pessoa]');
    const blocoEntidade = drawer.querySelector('[data-cp-entidade]');
    blocoPessoa.hidden = tipo !== 'pessoa';
    blocoEntidade.hidden = tipo !== 'entidade';
    drawer.querySelector('[data-cp-err]').hidden = true;
    drawer.querySelector('[data-cp-dup]').hidden = true;

    // Habilita inputs do bloco visível, desabilita do oculto — evita que
    // submit envie campos do tipo errado (names podem colidir entre blocos).
    const ativar = (bloco) => bloco.querySelectorAll('input, select, textarea').forEach(i => i.disabled = false);
    const desativar = (bloco) => bloco.querySelectorAll('input, select, textarea').forEach(i => i.disabled = true);
    if (tipo === 'pessoa') { ativar(blocoPessoa); desativar(blocoEntidade); }
    else { ativar(blocoEntidade); desativar(blocoPessoa); }

    // §01 e §02 abertas por padrão; §03+ colapsadas.
    const sections = (tipo === 'pessoa' ? blocoPessoa : blocoEntidade).querySelectorAll('.cp-sec');
    sections.forEach((s, i) => { s.open = i < 2; });

    // Popula tags via fetch (lazy: só uma vez por sessão de página).
    if (tipo === 'pessoa' && !drawer.dataset.tagsCarregadas) {
      popularTags(drawer);
    }

    drawer.classList.remove('hidden');
    drawer.setAttribute('aria-hidden', 'false');
    setTimeout(() => {
      const alvo = tipo === 'pessoa'
        ? form.querySelector('input[name=nome]')
        : form.querySelector('input[name=ent_nome]');
      if (alvo) alvo.focus();
    }, 50);
  }

  async function popularTags(drawer) {
    const sel = drawer.querySelector('select[data-cp-tags]');
    if (!sel) return;
    try {
      const resp = await fetch('/configuracoes/tags/buscar.json');
      if (!resp.ok) return;
      const data = await resp.json();
      sel.innerHTML = (data.resultados || [])
        .map((t) => `<option value="${t.id}">${t.label}</option>`)
        .join('');
      drawer.dataset.tagsCarregadas = '1';
    } catch (e) { /* silencioso: tags ficam vazias */ }
  }

  function fecharDrawerCriar() {
    const drawer = document.getElementById('drawer-criar-parte');
    if (!drawer) return;
    drawer.classList.add('hidden');
    drawer.setAttribute('aria-hidden', 'true');
    selectAlvoDoDrawer = null;
    inputAlvoDoDrawer = null;
  }

  function montarFormDataPessoa(form) {
    // Submete pro PessoaCreateView no mesmo formato do form completo —
    // mesmo schema de prefixos pros 3 formsets. A view detecta AJAX via
    // X-Requested-With e responde JSON com {slug_publico, label, ...}.
    const fd = new FormData();
    const csrf = form.querySelector('input[name=csrfmiddlewaretoken]').value;
    fd.append('csrfmiddlewaretoken', csrf);

    // §01 Identificação
    ['nome','sobrenome','nome_social','cpf','data_nascimento','genero'].forEach(n => {
      const el = form.querySelector(`[name=${n}]`);
      if (el) fd.append(n, el.value || '');
    });

    // §02 Contatos (3 formsets, 1 row cada)
    ['telefones','emails','redes_sociais'].forEach(prefix => {
      ['TOTAL_FORMS','INITIAL_FORMS','MIN_NUM_FORMS','MAX_NUM_FORMS'].forEach(k => {
        const el = form.querySelector(`input[name="${prefix}-${k}"]`);
        if (el) fd.append(`${prefix}-${k}`, el.value);
      });
    });
    // Linha 0 de telefones
    fd.append('telefones-0-numero', form.querySelector('[name="telefones-0-numero"]').value || '');
    fd.append('telefones-0-tipo', form.querySelector('[name="telefones-0-tipo"]').value);
    if (form.querySelector('[name="telefones-0-eh_whatsapp"]').checked) {
      fd.append('telefones-0-eh_whatsapp', 'on');
    }
    fd.append('telefones-0-rotulo', '');
    // Linha 0 de emails
    fd.append('emails-0-endereco', form.querySelector('[name="emails-0-endereco"]').value || '');
    fd.append('emails-0-rotulo', '');
    // Linha 0 de redes_sociais
    fd.append('redes_sociais-0-plataforma', form.querySelector('[name="redes_sociais-0-plataforma"]').value || '');
    fd.append('redes_sociais-0-valor', form.querySelector('[name="redes_sociais-0-valor"]').value || '');
    fd.append('redes_sociais-0-rotulo', '');

    // §03 Endereço (CEP preenche os ocultos via lookup)
    ['cep','logradouro','numero','complemento','bairro','cidade','estado'].forEach(n => {
      const el = form.querySelector(`[name=${n}]`);
      if (el) fd.append(n, el.value || '');
    });

    // §04 Tags (multi-select)
    const tagsSel = form.querySelector('select[data-cp-tags]');
    if (tagsSel) {
      Array.from(tagsSel.selectedOptions).forEach(o => fd.append('tags', o.value));
    }

    // §05 Observações
    const obs = form.querySelector('[name=observacoes]');
    if (obs) fd.append('observacoes', obs.value || '');

    return fd;
  }

  function montarFormDataEntidade(form) {
    // EntidadeCreateView agora roda no _EntidadeFormMixin (ADR 0057):
    // mesmos formsets de canal que Pessoa, só muda o dono. Aqui mapeio
    // os names `ent_*` do drawer pros names que o backend espera.
    const fd = new FormData();
    const csrf = form.querySelector('input[name=csrfmiddlewaretoken]').value;
    fd.append('csrfmiddlewaretoken', csrf);

    // §01 Identificação
    fd.append('nome', form.querySelector('[name=ent_nome]').value || '');
    fd.append('tipo', form.querySelector('[name=ent_tipo]').value);
    fd.append('nome_fantasia', form.querySelector('[name=ent_nome_fantasia]').value || '');
    fd.append('cnpj', form.querySelector('[name=ent_cnpj]').value || '');

    // §02 Contatos · 4 formsets, 1 row cada
    const mapearFormset = (prefix) => {
      ['TOTAL_FORMS','INITIAL_FORMS','MIN_NUM_FORMS','MAX_NUM_FORMS'].forEach(k => {
        const el = form.querySelector(`input[name="ent_${prefix}-${k}"]`);
        if (el) fd.append(`${prefix}-${k}`, el.value);
      });
    };
    mapearFormset('telefones');
    mapearFormset('emails');
    mapearFormset('redes_sociais');
    mapearFormset('sites');

    fd.append('telefones-0-numero', form.querySelector('[name="ent_telefones-0-numero"]').value || '');
    fd.append('telefones-0-tipo', form.querySelector('[name="ent_telefones-0-tipo"]').value);
    if (form.querySelector('[name="ent_telefones-0-eh_whatsapp"]').checked) {
      fd.append('telefones-0-eh_whatsapp', 'on');
    }
    fd.append('telefones-0-rotulo', '');

    fd.append('emails-0-endereco', form.querySelector('[name="ent_emails-0-endereco"]').value || '');
    fd.append('emails-0-rotulo', '');

    fd.append('redes_sociais-0-plataforma', form.querySelector('[name="ent_redes_sociais-0-plataforma"]').value || '');
    fd.append('redes_sociais-0-valor', form.querySelector('[name="ent_redes_sociais-0-valor"]').value || '');
    fd.append('redes_sociais-0-rotulo', '');

    fd.append('sites-0-url', form.querySelector('[name="ent_sites-0-url"]').value || '');
    fd.append('sites-0-rotulo', form.querySelector('[name="ent_sites-0-rotulo"]').value || '');

    // §03 Endereço
    fd.append('cep', form.querySelector('[name=ent_cep]').value || '');

    // §04 Observações
    fd.append('observacoes', form.querySelector('[name=ent_observacoes]').value || '');

    return fd;
  }

  function formatarErros(erros) {
    // Erros vêm como dicionário {campo: [mensagens]} ou aninhado pros formsets.
    // Lista plana com prefixo do campo.
    const partes = [];
    Object.entries(erros).forEach(([campo, lst]) => {
      if (Array.isArray(lst)) {
        partes.push(`<strong>${campo}:</strong> ${lst.join('; ')}`);
      } else if (typeof lst === 'object') {
        Object.entries(lst).forEach(([sub, msgs]) => {
          partes.push(`<strong>${campo} ${sub}:</strong> ${(msgs || []).join('; ')}`);
        });
      }
    });
    return partes.join('<br>');
  }

  async function submeterDrawerCriar(e) {
    e.preventDefault();
    const drawer = document.getElementById('drawer-criar-parte');
    const form = drawer.querySelector('[data-cp-form]');
    const tipo = form.dataset.cpTipo;
    const endpoint = ENDPOINTS_CRIAR[tipo];
    if (!endpoint || !selectAlvoDoDrawer) return;

    const submitBtn = drawer.querySelector('[data-cp-submit]');
    const errBox = drawer.querySelector('[data-cp-err]');
    errBox.hidden = true;
    submitBtn.disabled = true;
    const labelOriginal = submitBtn.textContent;
    submitBtn.textContent = 'Salvando…';

    const fd = tipo === 'pessoa' ? montarFormDataPessoa(form) : montarFormDataEntidade(form);

    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        body: fd,
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      const data = await resp.json();
      if (!resp.ok) {
        errBox.innerHTML = data.erros ? formatarErros(data.erros) : (data.erro || 'Erro ao criar.');
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
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = labelOriginal;
    }
  }

  // Máscaras compartilhadas no drawer
  function mascaraCPF(v) {
    const d = (v || '').replace(/\D/g, '').slice(0, 11);
    if (!d) return '';
    if (d.length <= 3) return d;
    if (d.length <= 6) return d.slice(0,3) + '.' + d.slice(3);
    if (d.length <= 9) return d.slice(0,3) + '.' + d.slice(3,6) + '.' + d.slice(6);
    return d.slice(0,3) + '.' + d.slice(3,6) + '.' + d.slice(6,9) + '-' + d.slice(9);
  }
  function mascaraTelefone(v) {
    const d = (v || '').replace(/\D/g, '').slice(0, 11);
    if (!d) return '';
    if (d.length <= 2) return '(' + d;
    if (d.length <= 6) return '(' + d.slice(0,2) + ') ' + d.slice(2);
    if (d.length <= 10) return '(' + d.slice(0,2) + ') ' + d.slice(2,6) + '-' + d.slice(6);
    return '(' + d.slice(0,2) + ') ' + d.slice(2,7) + '-' + d.slice(7);
  }
  function mascaraCEP(v) {
    const d = (v || '').replace(/\D/g, '').slice(0, 8);
    if (d.length <= 5) return d;
    return d.slice(0,5) + '-' + d.slice(5);
  }

  function aplicarMascaras(drawer) {
    drawer.addEventListener('input', (ev) => {
      const t = ev.target;
      if (!t || !t.dataset || !t.dataset.cpMask) return;
      let masked;
      if (t.dataset.cpMask === 'cpf') masked = mascaraCPF(t.value);
      else if (t.dataset.cpMask === 'tel') masked = mascaraTelefone(t.value);
      else if (t.dataset.cpMask === 'cep') masked = mascaraCEP(t.value);
      else return;
      if (masked !== t.value) t.value = masked;
    });

    // Lookup CEP no blur — preenche hidden inputs de endereço
    drawer.addEventListener('blur', async (ev) => {
      const t = ev.target;
      if (!t || t.name !== 'cep') return;
      const cep = (t.value || '').replace(/\D/g, '');
      if (cep.length !== 8) return;
      const status = drawer.querySelector('[data-cp-cep-status]');
      if (status) { status.textContent = 'Consultando…'; status.className = 'cp-status mute'; }
      try {
        const resp = await fetch(`/api/cep/${cep}/`);
        if (!resp.ok) {
          if (status) { status.textContent = 'CEP não encontrado.'; status.className = 'cp-status err'; }
          return;
        }
        const data = await resp.json();
        const form = drawer.querySelector('[data-cp-form]');
        ['logradouro','bairro','cidade','estado'].forEach(n => {
          const el = form.querySelector(`input[name=${n}]`);
          if (el) el.value = data[n] || '';
        });
        if (status) {
          status.textContent = `✓ ${data.cidade || ''}${data.estado ? ' / ' + data.estado : ''}`;
          status.className = 'cp-status ok';
        }
      } catch (e) {
        if (status) { status.textContent = 'Falha ao consultar.'; status.className = 'cp-status err'; }
      }
    }, true);
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
    aplicarMascaras(drawer);
    ativarDedup(drawer);

    // Botões externos (na seção Partes envolvidas) — abrem o drawer
    // apontando para o primeiro slot vazio do formset apropriado.
    document.querySelectorAll('[data-cp-abrir]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const tipo = btn.dataset.cpAbrir;
        const select = encontrarSlotVazio(tipo);
        if (!select) {
          alert('Não há slot disponível no formset. Recarregue a página.');
          return;
        }
        // Input "fake" — botão externo não tem um input de busca associado.
        // Quando o drawer salvar, vamos popular o autocomplete daquele slot.
        const inputBusca = select.parentElement.querySelector('input[type=text]');
        abrirDrawerCriar(tipo, '', select, inputBusca);
      });
    });
  }

  function encontrarSlotVazio(tipo) {
    // Pessoa: formset-row dentro de #formset-pessoas. Idem entidade.
    const prefix = tipo === 'pessoa' ? 'pessoas' : 'entidades';
    const formset = document.getElementById(`formset-${prefix}`);
    if (!formset) return null;
    const selects = formset.querySelectorAll(`select[data-autocomplete="${tipo}"]`);
    for (const s of selects) {
      if (!s.value) return s;
    }
    // Sem slot vazio — retorna o último (usuário verá overflow ou ajusta depois).
    // Idealmente teríamos "+ adicionar linha" no formset; deixado para iteração futura.
    return selects[selects.length - 1] || null;
  }

  // Dedup · ao digitar nome (entidade) ou nome+sobrenome (pessoa), consulta
  // o endpoint de busca e mostra possíveis duplicatas para o usuário evitar
  // criar registro repetido. Cada match tem botão "usar" que injeta direto
  // no autocomplete alvo e fecha o drawer.
  function ativarDedup(drawer) {
    let timer = null;
    drawer.addEventListener('input', (ev) => {
      const t = ev.target;
      if (!t || !t.matches) return;
      const form = drawer.querySelector('[data-cp-form]');
      const tipo = form.dataset.cpTipo;
      const relevante = tipo === 'pessoa'
        ? (t.name === 'nome' || t.name === 'sobrenome')
        : (t.name === 'ent_nome');
      if (!relevante) return;
      clearTimeout(timer);
      timer = setTimeout(() => buscarDuplicatas(drawer, tipo), 350);
    });
  }

  async function buscarDuplicatas(drawer, tipo) {
    const form = drawer.querySelector('[data-cp-form]');
    let q;
    if (tipo === 'pessoa') {
      const n = (form.querySelector('input[name=nome]').value || '').trim();
      const s = (form.querySelector('input[name=sobrenome]').value || '').trim();
      q = [n, s].filter(Boolean).join(' ');
    } else {
      q = (form.querySelector('input[name=ent_nome]').value || '').trim();
    }
    const bloco = drawer.querySelector('[data-cp-dup]');
    const lista = drawer.querySelector('[data-cp-dup-lista]');
    if (q.length < 3) {
      bloco.hidden = true;
      return;
    }
    const endpoint = ENDPOINTS[tipo];
    try {
      const resp = await fetch(endpoint + '?q=' + encodeURIComponent(q));
      if (!resp.ok) return;
      const data = await resp.json();
      const resultados = data.resultados || [];
      if (!resultados.length) {
        bloco.hidden = true;
        return;
      }
      lista.innerHTML = resultados.slice(0, 5).map((r) => `
        <li>
          <div class="dup-info">
            <span class="dup-nome">${escapeHtml(r.label)}</span>
            ${r.secundario ? `<span class="dup-ctx"> — ${escapeHtml(r.secundario)}</span>` : ''}
          </div>
          <button type="button" class="dup-usar" data-dup-id="${r.id}" data-dup-label="${escapeHtml(r.label)}">Usar este</button>
        </li>
      `).join('');
      lista.querySelectorAll('.dup-usar').forEach((b) => {
        b.addEventListener('click', () => {
          if (!selectAlvoDoDrawer) return;
          const id = b.dataset.dupId;
          const label = b.dataset.dupLabel;
          let opt = selectAlvoDoDrawer.querySelector(`option[value="${id}"]`);
          if (!opt) {
            opt = document.createElement('option');
            opt.value = id;
            opt.text = label;
            selectAlvoDoDrawer.appendChild(opt);
          }
          selectAlvoDoDrawer.value = id;
          if (inputAlvoDoDrawer) inputAlvoDoDrawer.value = label;
          selectAlvoDoDrawer.dispatchEvent(new Event('change', { bubbles: true }));
          fecharDrawerCriar();
        });
      });
      bloco.hidden = false;
    } catch (e) { /* silencioso */ }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[c]);
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

