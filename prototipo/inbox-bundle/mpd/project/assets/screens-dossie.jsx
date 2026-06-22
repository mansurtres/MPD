// Dossiê — detalhe da demanda. Coração do MPD.
// Três colunas: capa+partes (esq) · timeline (centro) · encaminhamentos+anexos (dir).

function Dossie({ d, onBack, onOpenPessoa }) {
  const [tab, setTab] = React.useState('dossie');
  const [tlFilter, setTlFilter] = React.useState('todas');
  const [composerOpen, setComposerOpen] = React.useState(false);
  const [composerTipo, setComposerTipo] = React.useState('Contato com pessoa');
  const [composerText, setComposerText] = React.useState('');
  const [localInteracoes, setLocalInteracoes] = React.useState(d.interacoes || []);

  // Group by date label
  const interacoesFiltradas = localInteracoes.filter(i => {
    if (tlFilter === 'todas') return true;
    if (tlFilter === 'manual') return !i.automatica;
    if (tlFilter === 'automaticas') return i.automatica;
    if (tlFilter === 'externo') return i.tipo === 'Encaminhamento externo' || i.tipo === 'Retorno externo recebido';
    return true;
  });

  function registerInteracao() {
    if (!composerText.trim()) return;
    const novo = {
      id: 'i-new-' + Date.now(),
      tipo: composerTipo,
      automatica: false,
      autor: window.MPD_DATA.usuarios.helena,
      data: 'agora',
      conteudo: composerText.trim(),
    };
    setLocalInteracoes([novo, ...localInteracoes]);
    setComposerText('');
    setComposerOpen(false);
  }

  return (
    <div data-screen-label="02 Dossiê — Demanda">
      <div className="dossie-header">
        <div className="crumbs">
          <a onClick={onBack}>Estante</a>
          <span className="sep">›</span>
          <a onClick={onBack}>Demandas</a>
          <span className="sep">›</span>
          <span className="mono" style={{fontSize: 11}}>{d.numero}</span>
        </div>

        <div className="dossie-hero">
          <div>
            <div className="dossie-num">
              <span className="big">{d.numero}</span>
              <span className="o">{d.origem === 'proativa' ? 'PROATIVA' : 'RESPONSIVA'}</span>
              <span className="o">{d.canal}</span>
              <span className="o">Aberta em {fmtDate(d.criadoEm)}</span>
            </div>
            <h1 className="dossie-title">{d.titulo}</h1>
            <div className="dossie-stamps">
              <span className={`stamp is-status-${d.status === 'em_andamento' ? 'andamento' : d.status}`}>
                {d.statusLabel}
              </span>
              <span className={`stamp is-pri-${d.prioridade}`}>
                <span className={`dot is-${d.prioridade}`}></span> {d.prioridade}
              </span>
              <span className="stamp">
                <span style={{color: 'var(--ink-3)'}}>Coord.</span> {d.coordenacao}
              </span>
              {(d.temas || []).map(t => (
                <span key={t} className="stamp" style={{background: 'var(--paper-2)', borderColor: 'transparent'}}>{t}</span>
              ))}
              {d.restrito && <span className="stamp" style={{borderColor: 'var(--stamp)', color: 'var(--stamp)'}}>● RESTRITA</span>}
            </div>
          </div>

          <div className="dossie-actions">
            <div className="big-stamp">
              {d.prioridade === 'urgente' ? 'URGENTE' : `vence em ${d.diasAteVencimento}d`}
            </div>
            <div className="row" style={{marginTop: 14}}>
              <button className="btn is-sm" onClick={() => setComposerOpen(true)}>+ Interação</button>
              <button className="btn is-sm">+ Encaminhar</button>
            </div>
            <div className="row">
              <button className="btn is-ghost is-sm">⋯ Mais</button>
              <button className="btn is-primary is-sm">Registrar devolutiva</button>
            </div>
          </div>
        </div>

        <div className="dossie-tabs">
          {[
            ['dossie', 'Dossiê'],
            ['timeline', `Timeline · ${localInteracoes.length}`],
            ['partes', `Partes · ${(d.partes||[]).length}`],
            ['encaminhamentos', `Encaminhamentos · ${(d.encaminhamentos||[]).length}`],
            ['anexos', `Anexos · ${(d.anexos||[]).length}`],
            ['historico', 'Histórico'],
          ].map(([key, label]) => (
            <div key={key}
                 className={`tab ${tab === key ? 'is-active' : ''}`}
                 onClick={() => setTab(key)}>
              {label}
            </div>
          ))}
        </div>
      </div>

      <div className="dossie-body">
        {/* Left col — capa */}
        <div className="dossie-col">
          <div className="col-block">
            <h4 className="col-h">Capa do processo</h4>
            <div className="memo">
              {d.descricao.split('\n\n').map((p, i) => <p key={i}>{p}</p>)}
            </div>
          </div>

          <div className="col-block">
            <h4 className="col-h">Metadados</h4>
            <dl className="meta-table">
              <dt>Protocolo</dt><dd className="mono" style={{fontSize: 12}}>{d.numero}</dd>
              <dt>Aberta em</dt><dd>{fmtDate(d.criadoEm)}</dd>
              <dt>Canal</dt><dd>{d.canal}</dd>
              <dt>Origem</dt><dd>{d.origem === 'proativa' ? 'Proativa' : 'Responsiva'}</dd>
              <dt>Coord.</dt><dd>{d.coordenacao}</dd>
              <dt>Responsável</dt>
              <dd>{d.responsavel
                ? <span style={{display: 'inline-flex', gap: 6, alignItems: 'center'}}>
                    <span className="avatar" style={{width: 20, height: 20, fontSize: 9}}>{d.responsavel.iniciais}</span>
                    {d.responsavel.nome}
                  </span>
                : <em>—</em>}
              </dd>
              <dt>Aberta por</dt>
              <dd>{d.criadoPor ? d.criadoPor.nome : '—'}</dd>
              {d.prazo && <><dt>Prazo</dt><dd className="mono" style={{fontSize: 12}}>{fmtDate(d.prazo)}</dd></>}
            </dl>
          </div>
        </div>

        {/* Center col — timeline */}
        <div className="dossie-col center">
          <div className="timeline-toolbar">
            <h4 className="col-h" style={{margin: 0}}>Timeline · {interacoesFiltradas.length}</h4>
            <div className="timeline-filter">
              {[['todas','Tudo'],['manual','Anotadas'],['automaticas','Automáticas'],['externo','Externas']].map(([k,l]) => (
                <span key={k}
                      className={`tl-chip ${tlFilter === k ? 'is-on' : ''}`}
                      onClick={() => setTlFilter(k)}>{l}</span>
              ))}
            </div>
          </div>

          {!composerOpen && (
            <button
              onClick={() => setComposerOpen(true)}
              style={{
                width: '100%', textAlign: 'left',
                fontFamily: 'var(--font-serif)', fontStyle: 'italic',
                fontSize: 14, color: 'var(--ink-3)',
                padding: '12px 14px',
                border: '1px dashed var(--rule)',
                background: 'var(--paper)',
                marginBottom: 18,
              }}>
              Registrar interação na demanda — anote contato, reunião, retorno externo…
            </button>
          )}
          {composerOpen && (
            <div className="tl-composer">
              <textarea
                placeholder="Descreva o que aconteceu. Use linguagem direta — esta nota fica no histórico para sempre."
                value={composerText}
                onChange={e => setComposerText(e.target.value)}
                autoFocus />
              <div className="tl-composer-toolbar">
                <div className="tl-tipo-select">
                  {['Contato com pessoa', 'Reunião', 'Anotação interna', 'Devolutiva'].map(t => (
                    <span key={t}
                          className={`tl-tipo ${composerTipo === t ? 'is-on' : ''}`}
                          onClick={() => setComposerTipo(t)}>{t}</span>
                  ))}
                </div>
                <div style={{display: 'flex', gap: 8}}>
                  <button className="btn is-ghost is-sm" onClick={() => { setComposerOpen(false); setComposerText(''); }}>Cancelar</button>
                  <button className="btn is-primary is-sm" onClick={registerInteracao}>Registrar</button>
                </div>
              </div>
            </div>
          )}

          <div className="timeline" style={{marginTop: 18}}>
            <TimelineGrouped interacoes={interacoesFiltradas} />
          </div>
        </div>

        {/* Right col — encaminhamentos + anexos + sidecar */}
        <div className="dossie-col">
          <div className="col-block">
            <h4 className="col-h">
              Encaminhamentos
              <span className="add">+ novo</span>
            </h4>
            {(d.encaminhamentos || []).map(e => <EncaminhamentoItem key={e.id} e={e} />)}
            {(!d.encaminhamentos || d.encaminhamentos.length === 0) && (
              <div className="empty" style={{padding: 18, textAlign: 'left'}}>Nenhum ofício, ligação ou requerimento ainda.</div>
            )}
          </div>

          <div className="col-block">
            <h4 className="col-h">
              Partes envolvidas
              <span className="add">+ adicionar</span>
            </h4>
            {(d.partes || []).map((p, i) => (
              <PartyItem key={i} p={p} onOpen={onOpenPessoa} />
            ))}
          </div>

          <div className="col-block">
            <h4 className="col-h">
              Anexos · {(d.anexos || []).length}
              <span className="add">+ enviar</span>
            </h4>
            {(d.anexos || []).map((a, i) => (
              <div className="anexo-item" key={i}>
                <div className="anexo-ico">{a.tipo === 'pdf' ? 'PDF' : a.tipo === 'img' ? 'IMG' : 'DOC'}</div>
                <div className="anexo-name">{a.nome}</div>
                <div className="anexo-meta">{a.tamanho}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function TimelineGrouped({ interacoes }) {
  // Agrupa por "label de data" (a primeira parte antes de " · ")
  const groups = [];
  let current = null;
  interacoes.forEach(i => {
    const dateLabel = (i.data || '').split('·')[0].trim();
    if (!current || current.label !== dateLabel) {
      current = { label: dateLabel, items: [] };
      groups.push(current);
    }
    current.items.push(i);
  });

  return (
    <>
      {groups.map((g, gi) => (
        <React.Fragment key={gi}>
          <div className="tl-date">{g.label}</div>
          {g.items.map(i => <TLItem key={i.id} i={i} />)}
        </React.Fragment>
      ))}
    </>
  );
}

function TLItem({ i }) {
  const klass = i.automatica ? 'is-auto'
    : i.tipo === 'Devolutiva' ? 'is-devolutiva'
    : i.status === 'agendada' ? 'is-agendada'
    : '';
  const hora = (i.data || '').split('·')[1] ? (i.data || '').split('·')[1].trim() : '';

  return (
    <div className={`tl-item ${klass}`}>
      <div className="tl-head">
        <span className="tipo">{i.tipo}</span>
        {hora && <span className="when">{hora}</span>}
        {i.canal && <span className="by">via <strong>{i.canal}</strong></span>}
        <span className="by">por <strong>{i.autor.nome.split(' ').slice(0,2).join(' ')}</strong></span>
        {i.automatica && <span className="auto-mark">auto</span>}
        {i.status === 'agendada' && <span className="auto-mark" style={{borderColor: 'var(--warn)', color: 'var(--warn)'}}>agendada</span>}
      </div>
      <div className={`tl-body ${i.automatica ? 'is-auto' : ''}`}>
        {i.conteudo}
      </div>
      {i.anexos && i.anexos.length > 0 && (
        <div className="tl-attach">
          {i.anexos.map((a, ai) => (
            <a key={ai}>
              <span className="ico">{a.tipo.toUpperCase()}</span>
              {a.nome}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

function EncaminhamentoItem({ e }) {
  const late = e.status === 'prazo_vencido';
  return (
    <div className="enc-item">
      <div className="enc-row1">
        <span className="enc-tipo">{e.tipoDoc}
          {e.numero && <span className="num">{e.numero}</span>}
        </span>
        <span className={`stamp is-status-${late ? 'aguardando' : 'andamento'}`}
              style={late ? {background: 'transparent', color: 'var(--stamp)', borderColor: 'var(--stamp)', borderStyle: 'dashed'} : {}}>
          {e.statusLabel}
        </span>
      </div>
      <div className="enc-target">{e.orgao}</div>
      {e.pessoa && <div style={{fontFamily: 'var(--font-sans)', fontSize: 11.5, color: 'var(--ink-3)', marginBottom: 4}}>a/c {e.pessoa}</div>}
      <div className="enc-dates">
        <span>enviado {e.envio}</span>
        {e.prazo && (
          <span className={late ? 'late' : ''}>
            prazo {e.prazo}{typeof e.diasParaPrazo === 'number' && e.diasParaPrazo < 0 ? ` (${Math.abs(e.diasParaPrazo)}d atrás)` : ''}
          </span>
        )}
      </div>
    </div>
  );
}

function PartyItem({ p, onOpen }) {
  const ref = p.ref || {};
  const isEnt = p.tipo === 'entidade';
  return (
    <div className="party" onClick={() => onOpen && onOpen(ref)}>
      <div className={`avatar ${isEnt ? 'is-entidade' : ''}`}>{ref.iniciais || (ref.sigla||'').slice(0,2)}</div>
      <div className="party-info">
        <div className="party-name">{ref.apelido || ref.nome}</div>
        <div className="party-meta">
          <span className="papel">{p.papel}</span>
          <span>{isEnt ? ref.tipo : (ref.bairro && `${ref.bairro}, ${ref.cidade || ''}`)}</span>
        </div>
      </div>
    </div>
  );
}

function fmtDate(iso) {
  if (!iso) return '—';
  const meses = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
  const [y, m, d] = iso.split('-');
  return `${parseInt(d, 10)}/${meses[parseInt(m, 10) - 1]}/${y}`;
}

window.Dossie = Dossie;
window.fmtDate = fmtDate;
