// Entrada — Inbox: capturas rápidas pendentes de triagem.
// Split view: lista à esquerda · processador à direita.

function Entrada({ itens: initialItens, onCreateDemanda }) {
  const [itens, setItens] = React.useState(initialItens);
  const [selId, setSelId] = React.useState(initialItens.find(x => x.status === 'pendente')?.id);
  const [decisao, setDecisao] = React.useState('demanda');

  const sel = itens.find(x => x.id === selId);

  // Auto-fields para "virar demanda"
  const [tituloPre, setTituloPre] = React.useState('');
  React.useEffect(() => {
    if (sel) {
      // Pega as primeiras palavras do conteúdo como sugestão de título
      const text = sel.conteudo.replace(/\s+/g, ' ').trim();
      setTituloPre(text.split('.')[0].slice(0, 80));
      setDecisao('demanda');
    }
  }, [selId]);

  function processar() {
    if (!sel) return;
    setItens(itens.map(x =>
      x.id === sel.id ? { ...x, status: 'processado', virouDemanda: 'MPD-2026-00353' } : x
    ));
    // Avança para o próximo pendente
    const pending = itens.filter(x => x.status === 'pendente' && x.id !== sel.id);
    if (pending.length > 0) setSelId(pending[0].id);
  }

  function descartar() {
    if (!sel) return;
    setItens(itens.map(x =>
      x.id === sel.id ? { ...x, status: 'descartado' } : x
    ));
    const pending = itens.filter(x => x.status === 'pendente' && x.id !== sel.id);
    if (pending.length > 0) setSelId(pending[0].id);
  }

  const pendentes = itens.filter(x => x.status === 'pendente').length;

  return (
    <div data-screen-label="03 Entrada">
      <div className="inbox-list-h" style={{borderBottom: '1px solid var(--rule)', padding: '14px 24px'}}>
        <div>
          <div className="toolbar-title" style={{fontSize: 22}}>
            Entrada
            <em>captura rápida → triagem</em>
          </div>
        </div>
        <div className="pending">
          <strong>{pendentes}</strong> pendente{pendentes !== 1 ? 's' : ''} · {itens.length - pendentes} processado/descartado
        </div>
      </div>

      <div className="inbox-layout">
        <div className="inbox-list">
          {itens.map(it => (
            <div key={it.id}
                 className={`inbox-item ${selId === it.id ? 'is-active' : ''} ${it.status !== 'pendente' ? 'is-done' : ''}`}
                 onClick={() => setSelId(it.id)}>
              <div className="inbox-meta">
                <span className="who">{it.autor.iniciais}</span>
                <span>{it.autor.nome.split(' ')[0]}</span>
                <span className="when">{it.capturadoEm}</span>
                {it.status === 'processado' && <span className="stamp is-status-concluida" style={{padding: '0 6px', fontSize: 9.5}}>→ {it.virouDemanda}</span>}
                {it.status === 'descartado' && <span className="stamp is-status-arquivado" style={{padding: '0 6px', fontSize: 9.5}}>DESCARTADO</span>}
              </div>
              <div className="ix-content">{it.conteudo}</div>
            </div>
          ))}
        </div>

        <div className="inbox-pane">
          {!sel ? (
            <div className="empty">Selecione um item da entrada.</div>
          ) : sel.status !== 'pendente' ? (
            <>
              <div className="inbox-pane-h">Item já processado</div>
              <div className="ix-quote-meta">
                <span>{sel.autor.nome}</span><span>{sel.capturadoEm}</span>
              </div>
              <blockquote className="ix-quote">{sel.conteudo}</blockquote>
              <div style={{fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-3)'}}>
                {sel.status === 'processado'
                  ? <>Este item virou a demanda <strong className="mono">{sel.virouDemanda}</strong>.</>
                  : <>Item descartado.</>}
              </div>
            </>
          ) : (
            <>
              <div className="inbox-pane-h">Triagem do item</div>
              <div>
                <div className="ix-quote-meta">
                  <span>{sel.autor.nome}</span>
                  <span>capturado {sel.capturadoEm}</span>
                </div>
                <blockquote className="ix-quote">{sel.conteudo}</blockquote>
              </div>

              <div>
                <div className="inbox-pane-h" style={{marginBottom: 8}}>Decisão</div>
                <div className="ix-decision">
                  <div className={`ix-choice ${decisao === 'demanda' ? 'is-on' : ''}`}
                       onClick={() => setDecisao('demanda')}>
                    <span className="key">D</span>
                    <h4>Virar demanda</h4>
                    <p>Tem alguém envolvido, ação concreta a ser tomada ou compromisso a registrar.</p>
                  </div>
                  <div className={`ix-choice ${decisao === 'fundir' ? 'is-on' : ''}`}
                       onClick={() => setDecisao('fundir')}>
                    <span className="key">F</span>
                    <h4>Fundir com existente</h4>
                    <p>Já existe uma demanda do mesmo assunto. Anexa o item como interação.</p>
                  </div>
                  <div className={`ix-choice ${decisao === 'descartar' ? 'is-on' : ''}`}
                       onClick={() => setDecisao('descartar')}>
                    <span className="key">X</span>
                    <h4>Descartar</h4>
                    <p>Lembrete pessoal, ruído ou já resolvido. Mantém histórico do item.</p>
                  </div>
                </div>
              </div>

              {decisao === 'demanda' && (
                <div>
                  <div className="inbox-pane-h" style={{marginBottom: 8}}>Esboço da demanda</div>
                  <div className="ix-form">
                    <div className="field" style={{gridColumn: '1 / -1'}}>
                      <label className="field-label">Título</label>
                      <input className="input" value={tituloPre} onChange={e => setTituloPre(e.target.value)} />
                    </div>
                    <div className="field">
                      <label className="field-label">Canal de entrada</label>
                      <select className="select">
                        <option>WhatsApp</option>
                        <option>Presencial</option>
                        <option>Telefone</option>
                        <option>DM Instagram</option>
                        <option>E-mail</option>
                      </select>
                    </div>
                    <div className="field">
                      <label className="field-label">Coordenação responsável</label>
                      <select className="select">
                        <option>Gabinete</option>
                        <option>Jurídico</option>
                        <option>Comunicação</option>
                      </select>
                    </div>
                    <div className="field">
                      <label className="field-label">Tema</label>
                      <input className="input" placeholder="ex.: Mobilidade, Saúde…" />
                    </div>
                    <div className="field">
                      <label className="field-label">Prioridade</label>
                      <select className="select">
                        <option>Normal</option>
                        <option>Alta</option>
                        <option>Urgente</option>
                        <option>Baixa</option>
                      </select>
                    </div>
                    <div className="field">
                      <label className="field-label">Solicitante (pessoa)</label>
                      <input className="input" placeholder="buscar pessoa cadastrada…" />
                    </div>
                    <div className="field">
                      <label className="field-label">Responsável</label>
                      <select className="select">
                        <option>Helena Carvalho</option>
                        <option>Marina Vidal</option>
                        <option>Rafael Monteiro</option>
                        <option>João Pessanha</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}

              {decisao === 'fundir' && (
                <div>
                  <div className="inbox-pane-h" style={{marginBottom: 8}}>Demanda existente</div>
                  <input className="input" placeholder="buscar por nº de protocolo ou título…" />
                  <div style={{marginTop: 12, fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--ink-3)'}}>
                    Sugestões: <span className="mono">MPD-2026-00346</span> · <span className="mono">MPD-2026-00344</span>
                  </div>
                </div>
              )}

              {decisao === 'descartar' && (
                <div>
                  <div className="inbox-pane-h" style={{marginBottom: 8}}>Motivo do descarte</div>
                  <input className="input" placeholder="Ex: lembrete pessoal, sem ação concreta" />
                </div>
              )}

              <div style={{display: 'flex', gap: 10, justifyContent: 'flex-end', paddingTop: 18, borderTop: '1px solid var(--rule)'}}>
                <button className="btn is-ghost is-sm" onClick={descartar}>Pular</button>
                {decisao === 'descartar' ? (
                  <button className="btn is-sm" onClick={descartar}>Descartar item</button>
                ) : decisao === 'fundir' ? (
                  <button className="btn is-primary is-sm" onClick={processar}>Anexar à demanda</button>
                ) : (
                  <button className="btn is-primary is-sm" onClick={processar}>Criar demanda →</button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

window.Entrada = Entrada;
