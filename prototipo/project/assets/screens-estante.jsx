// Estante — lista de demandas
// Tela principal de trabalho. Linhas tipo aba/lombada de dossiê.

function Estante({ onOpenDemanda, demandas, navigate }) {
  const [filtro, setFiltro] = React.useState('todas');
  const [coord, setCoord] = React.useState('todas');

  const filtros = [
    { key: 'todas', label: 'Todas', count: demandas.length },
    { key: 'novo', label: 'Novas', count: demandas.filter(d => d.status === 'novo').length },
    { key: 'em_andamento', label: 'Em andamento', count: demandas.filter(d => d.status === 'em_andamento').length },
    { key: 'aguardando_terceiros', label: 'Aguardando terceiros', count: demandas.filter(d => d.status === 'aguardando_terceiros').length },
    { key: 'concluida', label: 'Concluídas', count: demandas.filter(d => d.status === 'concluida').length },
    { key: 'minhas', label: 'Sob minha responsa.', count: demandas.filter(d => d.responsavel && d.responsavel.id === 'u2').length },
  ];

  const coords = [
    { key: 'todas', label: 'Todas', count: demandas.length },
    { key: 'Gabinete', label: 'Gabinete', count: demandas.filter(d => d.coordenacao === 'Gabinete').length },
    { key: 'Jurídico', label: 'Jurídico', count: demandas.filter(d => d.coordenacao === 'Jurídico').length },
    { key: 'Comunicação', label: 'Comunicação', count: demandas.filter(d => d.coordenacao === 'Comunicação').length },
  ];

  const temas = [
    { key: 'Saúde', n: 14 },
    { key: 'Mobilidade urbana', n: 22 },
    { key: 'Saneamento', n: 9 },
    { key: 'Educação', n: 11 },
    { key: 'Iluminação pública', n: 6 },
    { key: 'Espaços públicos', n: 7 },
    { key: 'Tributação', n: 3 },
  ];

  let lista = demandas;
  if (filtro === 'minhas') {
    lista = lista.filter(d => d.responsavel && d.responsavel.id === 'u2');
  } else if (filtro !== 'todas') {
    lista = lista.filter(d => d.status === filtro);
  }
  if (coord !== 'todas') lista = lista.filter(d => d.coordenacao === coord);

  return (
    <div className="estante" data-screen-label="01 Estante">
      <aside className="estante-rail">
        <div className="rail-group">
          <h4 className="rail-h">Bandeja</h4>
          <ul className="rail-list">
            {filtros.map(f => (
              <li key={f.key}
                  className={`rail-item ${filtro === f.key ? 'is-active' : ''}`}
                  onClick={() => setFiltro(f.key)}>
                <span>{f.label}</span>
                <span className="ct">{f.count}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rail-group">
          <h4 className="rail-h">Coordenação</h4>
          <ul className="rail-list">
            {coords.map(c => (
              <li key={c.key}
                  className={`rail-item ${coord === c.key ? 'is-active' : ''}`}
                  onClick={() => setCoord(c.key)}>
                <span>{c.label}</span>
                <span className="ct">{c.count}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rail-group">
          <h4 className="rail-h">Temas</h4>
          <ul className="rail-list">
            {temas.map(t => (
              <li key={t.key} className="rail-item">
                <span>{t.key}</span>
                <span className="ct">{t.n}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rail-group">
          <h4 className="rail-h">Visões salvas</h4>
          <ul className="rail-list">
            <li className="rail-item"><span>Vencendo essa semana</span><span className="ct">7</span></li>
            <li className="rail-item"><span>Sem resposta ext. (&gt;15d)</span><span className="ct">4</span></li>
            <li className="rail-item"><span>Restritas</span><span className="ct">2</span></li>
          </ul>
        </div>
      </aside>

      <section className="estante-body">
        <div className="toolbar">
          <div className="toolbar-left">
            <div className="toolbar-title">
              Demandas
              <em>{lista.length} de {demandas.length}</em>
            </div>
          </div>
          <div className="toolbar-right">
            <div className="search">
              <span style={{fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-3)'}}>buscar</span>
              <input placeholder="nº de protocolo, título, pessoa, bairro…" />
              <span className="kbd">⌘K</span>
            </div>
            <button className="btn is-sm">Ordenar: mais recentes</button>
            <button className="btn is-primary is-sm">+ Nova demanda</button>
          </div>
        </div>

        <ul className="dem-list">
          {lista.map(d => <DemRow key={d.numero} d={d} onOpen={() => onOpenDemanda(d)} />)}
        </ul>

        {lista.length === 0 && (
          <div className="empty">Nenhuma demanda nesse filtro.</div>
        )}
      </section>
    </div>
  );
}

function DemRow({ d, onOpen }) {
  const statusKey = d.status === 'concluida' ? 'concluida'
    : d.status === 'arquivado' ? 'arquivado'
    : d.status === 'novo' ? 'novo'
    : d.status === 'em_andamento' ? 'andamento'
    : 'aguardando';

  const partsLine = (d.partes || []).slice(0, 2)
    .map(p => p.ref ? (p.ref.apelido || p.ref.nome || p.ref.sigla) : '').filter(Boolean);
  const morePartes = (d.partes || []).length - partsLine.length;

  const daysLeft = d.diasAteVencimento;
  let prazoKlass = '';
  if (typeof daysLeft === 'number') {
    if (daysLeft < 0) prazoKlass = 'is-late';
    else if (daysLeft <= 3) prazoKlass = 'is-near';
  }

  return (
    <li className="dem-row" onClick={onOpen}>
      <div className="dem-num">
        <span className="n">{d.numero}</span>
        <span className="o">{d.origem === 'proativa' ? '↗ Proativa' : '↘ Responsiva'} · {d.canal}</span>
      </div>
      <div className="dem-title">
        <h3>{d.titulo}</h3>
        <div className="meta">
          <span className="tema">{d.tema}</span>
          <span className="sep">·</span>
          <span>{d.coordenacao}</span>
          {d.prioridade === 'urgente' && (
            <React.Fragment>
              <span className="sep">·</span>
              <span style={{color: 'var(--stamp)', fontWeight: 600, textTransform: 'uppercase', fontSize: 10.5, letterSpacing: '.08em'}}>URGENTE</span>
            </React.Fragment>
          )}
        </div>
      </div>
      <div className="dem-parties">
        {partsLine.length > 0 ? (
          <>
            <span>{partsLine.join(' · ')}</span>
            {morePartes > 0 && <span className="more">+ {morePartes} parte{morePartes > 1 ? 's' : ''}</span>}
          </>
        ) : (
          <span style={{color: 'var(--ink-4)', fontStyle: 'normal', fontSize: 12}}>—</span>
        )}
      </div>
      <div className={`dem-prazo ${prazoKlass}`}>
        {d.status === 'concluida' ? (
          <>
            <span className="lbl">Concluída</span>
            <span>{d.concluidoEm}</span>
          </>
        ) : d.prazo ? (
          <>
            <span className="lbl">Prazo</span>
            <span>
              {daysLeft < 0 ? `${Math.abs(daysLeft)}d atrasado`
                : daysLeft === 0 ? 'Hoje'
                : `em ${daysLeft}d`}
            </span>
          </>
        ) : (
          <span className="lbl">Sem prazo</span>
        )}
      </div>
      <div className="dem-status">
        {d.status === 'concluida' ? (
          <span className={`stamp is-result-${(d.resultado || 'pendente').replace('atendido_parcialmente','parcialmente')}`}>
            {d.resultadoLabel || 'Atendida'}
          </span>
        ) : (
          <span className={`stamp is-status-${statusKey}`}>{d.statusLabel}</span>
        )}
        <span className="resp">
          {d.responsavel ? d.responsavel.nome.split(' ')[0] : <em style={{color: 'var(--ink-4)'}}>sem responsável</em>}
        </span>
      </div>
    </li>
  );
}

window.Estante = Estante;
