// MPD — App shell. Navega entre Estante, Dossiê, Entrada e Pessoa.

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "palette": "musgo",
  "density": "comfy",
  "novelty": "equilibrio",
  "bodyType": "serif"
}/*EDITMODE-END*/;

function App() {
  const { demandas, demandaAtual, pessoas, inboxItens } = window.MPD_DATA;
  const [route, setRoute] = React.useState({ name: 'estante' });
  const [t, setTweak] = window.useTweaks(TWEAK_DEFAULTS);

  // Atalho — Ctrl+K abre command palette (placeholder)
  React.useEffect(() => {
    function onKey(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.querySelector('.search input')?.focus();
      }
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  const navItems = [
    { key: 'estante', label: 'Estante', count: demandas.filter(d => d.status !== 'concluida' && d.status !== 'arquivado').length },
    { key: 'entrada', label: 'Entrada', count: inboxItens.filter(i => i.status === 'pendente').length },
    { key: 'pessoas', label: 'Pessoas' },
    { key: 'encaminhamentos', label: 'Encaminhamentos', count: 12 },
    { key: 'pendencias', label: 'Pendências', count: 3 },
    { key: 'analise', label: 'Análise' },
  ];

  function openDemanda(d) {
    // Se for a #347 traz dados completos
    const full = demandas.find(x => x.numero === d.numero) || demandaAtual;
    setRoute({ name: 'dossie', demanda: full.interacoes ? full : demandaAtual });
  }

  function openPessoa(p) {
    const full = pessoas[Object.keys(pessoas).find(k => pessoas[k].id === p.id)] || pessoas.dona_geni;
    setRoute({ name: 'pessoa', pessoa: full });
  }

  function navigate(name) {
    if (name === 'pessoas') setRoute({ name: 'pessoa', pessoa: pessoas.dona_geni });
    else setRoute({ name });
  }

  return (
    <div className="app"
         data-palette={t.palette}
         data-density={t.density}
         data-novelty={t.novelty}
         data-body-type={t.bodyType}
         style={t.bodyType === 'sans' ? { '--font-serif': 'var(--font-sans)' } : {}}>

      {/* Faixa institucional */}
      <div className="gov-bar">
        <div className="left">
          <span>MANDATO PARLAMENTAR DIGITAL</span>
          <span className="dot"></span>
          <span>VEREADOR PEDRO TRÉS · CMV · LEG. 2025—2028</span>
        </div>
        <div className="right">
          <span>v0.4 · Ambiente de produção</span>
        </div>
      </div>

      {/* Cabeçalho com identidade + tabs */}
      <header className="head">
        <div className="head-row">
          <div className="brand">
            <div className="brand-mark">
              MPD<span className="acc">.</span>
            </div>
            <div className="brand-sub">
              Gabinete Pedro Trés <span style={{margin: '0 8px', color: 'var(--rule)'}}>·</span> Vitória / ES
            </div>
          </div>
          <div className="user-strip">
            {route.name !== 'entrada' && inboxItens.filter(i => i.status === 'pendente').length > 0 && (
              <span className="pill alert">
                {inboxItens.filter(i => i.status === 'pendente').length} no inbox
              </span>
            )}
            <span>Helena C. · Chefe de Gabinete</span>
            <span className="pill">HC</span>
          </div>
        </div>
        <nav className="tabs">
          {navItems.map(n => (
            <div key={n.key}
                 className={`tab ${route.name === n.key || (route.name === 'dossie' && n.key === 'estante') || (route.name === 'pessoa' && n.key === 'pessoas') ? 'is-active' : ''}`}
                 onClick={() => navigate(n.key)}>
              {n.label}
              {typeof n.count === 'number' && <span className="count">{n.count}</span>}
            </div>
          ))}
        </nav>
      </header>

      {/* Conteúdo */}
      <main className="main">
        {route.name === 'estante' && (
          <Estante demandas={demandas}
                   onOpenDemanda={openDemanda}
                   navigate={navigate} />
        )}
        {route.name === 'dossie' && (
          <Dossie d={route.demanda}
                  onBack={() => setRoute({ name: 'estante' })}
                  onOpenPessoa={openPessoa} />
        )}
        {route.name === 'entrada' && (
          <Entrada itens={inboxItens} onCreateDemanda={openDemanda} />
        )}
        {route.name === 'pessoa' && (
          <Pessoa p={route.pessoa}
                  onBack={() => setRoute({ name: 'estante' })}
                  onOpenDemanda={openDemanda}
                  demandas={demandas} />
        )}
        {(route.name === 'encaminhamentos' || route.name === 'pendencias' || route.name === 'analise') && (
          <PlaceholderTela nome={navItems.find(x => x.key === route.name).label} />
        )}
      </main>

      {/* FAB de captura rápida (consistente com o MVP atual) */}
      <button className="fab" onClick={() => navigate('entrada')}>
        <span className="plus">+</span>
        Captura rápida
        <span className="kbd">⌘ K</span>
      </button>

      <MpdTweaks t={t} setTweak={setTweak} />
    </div>
  );
}

function PlaceholderTela({ nome }) {
  return (
    <div style={{padding: '60px 24px', maxWidth: 700, margin: '0 auto', textAlign: 'left'}}
         data-screen-label={`05 ${nome}`}>
      <div style={{fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--ink-3)', marginBottom: 8}}>
        Tela ainda não desenhada
      </div>
      <h1 style={{fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 32, letterSpacing: '-0.02em', margin: '0 0 18px'}}>{nome}</h1>
      <p style={{fontFamily: 'var(--font-serif)', fontSize: 16, lineHeight: 1.6, color: 'var(--ink-2)'}}>
        Esta área existe no sistema e está no roadmap, mas neste protótipo o foco
        foi em <strong>Estante</strong>, <strong>Dossiê de Demanda</strong>,
        <strong> Entrada</strong> e <strong>Pessoa</strong> — onde o design system aparece em mais densidade.
        Use o painel de Tweaks para alternar paleta, densidade e tipografia.
      </p>
      <div style={{marginTop: 24, border: '1px dashed var(--rule)', padding: 18, background: 'var(--paper-2)'}}>
        <div style={{fontFamily: 'var(--font-sans)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '.08em', color: 'var(--ink-3)', marginBottom: 6}}>
          O que viria aqui
        </div>
        <div style={{fontFamily: 'var(--font-serif)', fontSize: 14, color: 'var(--ink)'}}>
          {nome === 'Encaminhamentos' && 'Lista de todos os ofícios, requerimentos e ligações já enviados. Filtros por status, prazo vencido, órgão destinatário. Vista de prazos a vencer.'}
          {nome === 'Pendências' && 'Bandeja de pendências do assessor logado — interações agendadas, prazos vencendo, devolutivas atrasadas, encaminhamentos sem resposta.'}
          {nome === 'Análise' && 'Visões agregadas: temas mais frequentes, mapa de calor por bairro, prazos médios, taxa de atendimento por coordenação.'}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Tweaks
// ============================================================

const PALETTES = {
  musgo:   ['#506b40', '#3a4f30', '#f6f1e4'],
  bordo:   ['#7b3636', '#5e2828', '#f6f1e4'],
  marinho: ['#324b6e', '#23355a', '#f6f1e4'],
};

function MpdTweaks({ t, setTweak }) {
  const Tw = window.TweaksPanel;
  const { TweakSection, TweakRadio, TweakColor } = window;

  const paletteValue = PALETTES[t.palette] || PALETTES.musgo;

  return (
    <Tw title="Tweaks · MPD">
      <TweakSection label="Paleta">
        <TweakColor
          label="Acento institucional"
          options={[PALETTES.musgo, PALETTES.bordo, PALETTES.marinho]}
          value={paletteValue}
          onChange={(v) => {
            const palette = v[0] === '#506b40' ? 'musgo'
                          : v[0] === '#7b3636' ? 'bordo'
                          : 'marinho';
            setTweak('palette', palette);
          }} />
      </TweakSection>

      <TweakSection label="Tipografia">
        <TweakRadio
          label="Texto corrido"
          value={t.bodyType}
          onChange={v => setTweak('bodyType', v)}
          options={[
            { value: 'serif', label: 'Serif' },
            { value: 'sans',  label: 'Sans' },
          ]} />
      </TweakSection>

      <TweakSection label="Densidade">
        <TweakRadio
          label="Espaço"
          value={t.density}
          onChange={v => setTweak('density', v)}
          options={[
            { value: 'compact', label: 'Compacta' },
            { value: 'comfy',   label: 'Padrão' },
          ]} />
      </TweakSection>

      <TweakSection label="Ousadia visual">
        <TweakRadio
          label="Tom"
          value={t.novelty}
          onChange={v => setTweak('novelty', v)}
          options={[
            { value: 'sobrio',     label: 'Sóbrio' },
            { value: 'equilibrio', label: 'Equilíbrio' },
            { value: 'expressivo', label: 'Expressivo' },
          ]} />
      </TweakSection>
    </Tw>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
