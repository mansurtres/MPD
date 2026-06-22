// Pessoa — perfil de constituinte. Card de identidade + histórico de demandas.

function Pessoa({ p, onOpenDemanda, onBack, demandas }) {
  // Demandas relacionadas a essa pessoa
  const relacionadas = (demandas || []).filter(d =>
    (d.partes || []).some(pt => pt.tipo === 'pessoa' && pt.ref && pt.ref.id === p.id)
  );

  // Mock: se não houver, gera duas como exemplo
  const fakeRelacionadas = [
    { numero: 'MPD-2025-00091', titulo: 'Pedido de manutenção da praça da Constante Sodré', concluidoEm: '12/dez/2025', resultadoLabel: 'Atendido' },
    { numero: 'MPD-2025-00184', titulo: 'Apoio para festa junina da comunidade do Suá', concluidoEm: '06/jul/2025', resultadoLabel: 'Atendido parcialmente' },
  ];

  return (
    <div data-screen-label="04 Pessoa">
      <div className="crumbs" style={{padding: '12px 24px 0'}}>
        <a onClick={onBack}>Estante</a>
        <span className="sep">›</span>
        <a onClick={onBack}>Pessoas</a>
        <span className="sep">›</span>
        <span>{p.apelido || p.nome}</span>
      </div>

      <div className="pessoa-layout">
        {/* Card de identidade */}
        <div className="pessoa-card">
          <div className="pessoa-card-h">
            <div className="avatar lg">{p.iniciais}</div>
            <div className="who">
              <h2>{p.apelido || p.nome}</h2>
              {p.apelido && (
                <div style={{fontFamily: 'var(--font-serif)', fontStyle: 'italic', fontSize: 13, color: 'var(--ink-3)', marginBottom: 4}}>
                  {p.nome}
                </div>
              )}
              <div className="id mono">slug-{p.id}</div>
            </div>
          </div>
          <div className="pessoa-card-body">
            <div className="contact-row"><span className="lbl">Bairro</span><span className="val">{p.bairro}</span></div>
            <div className="contact-row"><span className="lbl">Cidade</span><span className="val">{p.cidade}</span></div>
            {p.cep && <div className="contact-row"><span className="lbl">CEP</span><span className="val mono">{p.cep}</span></div>}
          </div>

          <div className="pessoa-section">
            <h4>Contato</h4>
            {(p.telefones || []).map((t, i) => (
              <div className="contact-row" key={i}>
                <span className="lbl">{t.tipo}</span>
                <span className="val mono">{t.valor}</span>
                {t.wpp && <span className="tag is-on">WhatsApp</span>}
              </div>
            ))}
            {(p.emails || []).map((e, i) => (
              <div className="contact-row" key={'e'+i}>
                <span className="lbl">E-mail</span>
                <span className="val">{e}</span>
              </div>
            ))}
            {(p.redes || []).map((r, i) => (
              <div className="contact-row" key={'r'+i}>
                <span className="lbl">{r.plataforma}</span>
                <span className="val">{r.valor}</span>
              </div>
            ))}
          </div>

          {p.tags && p.tags.length > 0 && (
            <div className="pessoa-section">
              <h4>Tags / Caracterização</h4>
              <div className="tag-row">
                {p.tags.map(t => <span key={t} className="tag">{t}</span>)}
              </div>
            </div>
          )}

          {p.observacoes && (
            <div className="pessoa-section">
              <h4>Observações</h4>
              <div style={{fontFamily: 'var(--font-serif)', fontSize: 13.5, lineHeight: 1.55, color: 'var(--ink-2)'}}>
                {p.observacoes}
              </div>
            </div>
          )}

          <div className="pessoa-section" style={{display: 'flex', gap: 8}}>
            <button className="btn is-sm">Editar</button>
            <button className="btn is-ghost is-sm">+ Vincular entidade</button>
          </div>
        </div>

        {/* Right column — histórico de demandas + atividade */}
        <div>
          <div style={{display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8}}>
            <h3 style={{fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 20, letterSpacing: '-0.01em', margin: 0}}>
              Histórico de demandas
              <em style={{fontFamily: 'var(--font-mono)', fontStyle: 'normal', fontSize: 12, color: 'var(--ink-3)', marginLeft: 10}}>
                {relacionadas.length + fakeRelacionadas.length} no total
              </em>
            </h3>
            <button className="btn is-primary is-sm">+ Abrir nova demanda</button>
          </div>

          <ul className="hist-list">
            {relacionadas.map(d => (
              <li key={d.numero} className="hist-item" onClick={() => onOpenDemanda(d)}>
                <span className="num">{d.numero}</span>
                <div>
                  <div className="titulo">{d.titulo}</div>
                  <div style={{fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--ink-3)', marginTop: 2, display: 'flex', gap: 10, alignItems: 'center'}}>
                    <span className={`stamp is-status-${d.status === 'em_andamento' ? 'andamento' : d.status}`} style={{padding: '1px 6px', fontSize: 9.5}}>
                      {d.statusLabel}
                    </span>
                    <span>{d.tema}</span>
                    <span>{(d.partes || []).find(pt => pt.tipo === 'pessoa' && pt.ref.id === p.id)?.papel}</span>
                  </div>
                </div>
                <span className="when">aberta {window.fmtDate(d.criadoEm)}</span>
              </li>
            ))}
            {fakeRelacionadas.map(d => (
              <li key={d.numero} className="hist-item">
                <span className="num">{d.numero}</span>
                <div>
                  <div className="titulo">{d.titulo}</div>
                  <div style={{fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--ink-3)', marginTop: 2, display: 'flex', gap: 10, alignItems: 'center'}}>
                    <span className="stamp is-result-atendido" style={{padding: '1px 6px', fontSize: 9.5}}>
                      {d.resultadoLabel}
                    </span>
                  </div>
                </div>
                <span className="when">concl. {d.concluidoEm}</span>
              </li>
            ))}
          </ul>

          <h3 style={{fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 18, letterSpacing: '-0.01em', margin: '32px 0 8px'}}>
            Vínculos
          </h3>
          <div style={{display: 'flex', gap: 10, flexWrap: 'wrap'}}>
            <VinculoCard nome="Associação de Moradores do Suá" papel="Presidente" desde="2014" />
            <VinculoCard nome="Conselho Comunitário de Segurança — Praia do Suá" papel="Conselheira titular" desde="2022" />
          </div>

          <h3 style={{fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 18, letterSpacing: '-0.01em', margin: '32px 0 8px'}}>
            Linha do tempo de contato
          </h3>
          <div className="timeline" style={{paddingLeft: 28}}>
            <div className="tl-date">Esta semana</div>
            <div className="tl-item">
              <div className="tl-head">
                <span className="tipo">WhatsApp</span>
                <span className="when">11/mai · 16:48</span>
                <span className="by">por <strong>Marina Vidal</strong></span>
              </div>
              <div className="tl-body">Retorno parcial sobre a demanda <span className="mono">MPD-2026-00347</span> (iluminação na Henrique Moscoso). Combinado novo contato no dia 18.</div>
            </div>
            <div className="tl-item">
              <div className="tl-head">
                <span className="tipo">Reunião</span>
                <span className="when">04/mai · 19:10</span>
                <span className="by">por <strong>Marina Vidal</strong></span>
              </div>
              <div className="tl-body">Vistoria presencial com Dona Geni e 5 moradores. Confirmados 11 pontos de iluminação apagados.</div>
            </div>

            <div className="tl-date">Anteriormente</div>
            <div className="tl-item">
              <div className="tl-head">
                <span className="tipo">DM Instagram</span>
                <span className="when">12/dez/2025</span>
                <span className="by">por <strong>Luiza Tavares</strong></span>
              </div>
              <div className="tl-body is-auto">Conclusão da demanda MPD-2025-00091 — agradecimento e foto da praça reformada.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function VinculoCard({ nome, papel, desde }) {
  return (
    <div style={{
      border: '1px solid var(--rule)',
      background: 'var(--paper)',
      padding: '12px 14px',
      minWidth: 260,
      maxWidth: 360,
    }}>
      <div style={{fontFamily: 'var(--font-sans)', fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--accent-ink)', background: 'var(--accent-soft)', display: 'inline-block', padding: '1px 6px', marginBottom: 6}}>
        {papel}
      </div>
      <div style={{fontFamily: 'var(--font-sans)', fontSize: 14, fontWeight: 500, color: 'var(--ink)', marginBottom: 2}}>
        {nome}
      </div>
      <div style={{fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-3)'}}>
        vigente · desde {desde}
      </div>
    </div>
  );
}

window.Pessoa = Pessoa;
