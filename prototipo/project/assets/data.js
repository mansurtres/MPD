// MPD — Dados de exemplo realistas
// Vereador Pedro Trés (fictício, mas inspirado no contexto ES)

window.MPD_DATA = (function () {
  const usuarios = {
    pedro:    { id: 'u1', nome: 'Pedro Trés',          iniciais: 'PT', papel: 'Vereador' },
    helena:   { id: 'u2', nome: 'Helena Carvalho',     iniciais: 'HC', papel: 'Chefe de Gabinete' },
    rafael:   { id: 'u3', nome: 'Rafael Monteiro',     iniciais: 'RM', papel: 'Assessor — Jurídico' },
    marina:   { id: 'u4', nome: 'Marina Vidal',        iniciais: 'MV', papel: 'Assessora — Mobilidade' },
    joao:     { id: 'u5', nome: 'João Pessanha',       iniciais: 'JP', papel: 'Assessor — Saúde' },
    luiza:    { id: 'u6', nome: 'Luiza Tavares',       iniciais: 'LT', papel: 'Comunicação' },
  };

  const pessoas = {
    dona_geni: {
      id: 'p1',
      nome: 'Genilda Maria dos Santos',
      apelido: 'Dona Geni',
      iniciais: 'GS',
      bairro: 'Praia do Suá',
      cidade: 'Vitória — ES',
      cep: '29050-110',
      telefones: [{ tipo: 'Celular', valor: '(27) 99812-4471', wpp: true }],
      emails: [],
      redes: [{ plataforma: 'Instagram', valor: '@dona.geni.vix' }],
      tags: ['Líder comunitária', 'Associação de moradores', 'Idosa'],
      observacoes: 'Presidente da Associação de Moradores do Suá há 12 anos. Articula moradores em torno de demandas de saneamento e iluminação. Contato preferido por WhatsApp em horário comercial.',
      origem: 'manual',
    },
    seu_donato: {
      id: 'p2', nome: 'Donato Vieira da Silva', iniciais: 'DV',
      bairro: 'Jardim Camburi', cidade: 'Vitória — ES',
      telefones: [{ tipo: 'Celular', valor: '(27) 99645-2087', wpp: true }],
      tags: ['Microempresa', 'Comerciante'],
    },
    ana: {
      id: 'p3', nome: 'Ana Paula Ferreira', iniciais: 'AF',
      bairro: 'Jardim da Penha', cidade: 'Vitória — ES',
      telefones: [{ tipo: 'Celular', valor: '(27) 98203-1144', wpp: true }],
      tags: ['Profissional de saúde'],
    },
    professor: {
      id: 'p4', nome: 'Marcelo Antunes Borges', iniciais: 'MB',
      bairro: 'Maruípe', cidade: 'Vitória — ES',
      tags: ['Educação', 'Servidor público'],
    },
    motorista: {
      id: 'p5', nome: 'Cláudio Rocha Pimentel', iniciais: 'CP',
      bairro: 'São Pedro', cidade: 'Vitória — ES',
      tags: ['Transporte', 'Cooperativa'],
    },
  };

  const entidades = {
    amsua: {
      id: 'e1', nome: 'Associação de Moradores do Suá', tipo: 'Associação de moradores',
      sigla: 'AM-SUÁ', cidade: 'Vitória — ES',
      tags: ['Movimento comunitário'],
    },
    sec_obras: {
      id: 'e2', nome: 'Secretaria Municipal de Obras', tipo: 'Órgão público',
      sigla: 'SEMOB',
    },
    cmv: {
      id: 'e3', nome: 'Câmara Municipal de Vitória', tipo: 'Órgão público',
      sigla: 'CMV',
    },
    ubs_pra_sua: {
      id: 'e4', nome: 'UBS Praia do Suá', tipo: 'Órgão público',
      sigla: 'UBS PSU',
    },
  };

  // --- Demandas (foco no detalhe da #347) ---
  const demandas = [
    {
      numero: 'MPD-2026-00347',
      slug: 'd347',
      titulo: 'Iluminação pública precária na Rua Henrique Moscoso após poda de árvores',
      descricao:
`Moradores da Rua Henrique Moscoso (trecho entre os números 800 e 1100, Praia do Suá) relatam que, após poda de árvores realizada pela prefeitura em 28/abr, várias luminárias permaneceram apagadas ou com lâmpadas queimadas.

A iluminação é descrita como "deficiente, com trechos completamente escuros à noite", o que tem aumentado a sensação de insegurança e gerado relatos de furtos a transeuntes.

Dona Geni (presidente da AM-Suá) protocolou abaixo-assinado com 87 assinaturas. Pede vistoria técnica e troca das lâmpadas, além de avaliação sobre a poda ter sido excessiva — algumas árvores foram drasticamente reduzidas, alterando o sombreamento.`,
      origem: 'responsiva',
      canal: 'WhatsApp',
      status: 'em_andamento',
      statusLabel: 'Em andamento',
      resultado: 'pendente',
      prioridade: 'alta',
      coordenacao: 'Gabinete',
      tema: 'Iluminação pública',
      temas: ['Iluminação pública', 'Mobilidade urbana'],
      responsavel: usuarios.marina,
      criadoPor: usuarios.helena,
      criadoEm: '2026-05-02',
      prazo: '2026-05-20',
      diasAteVencimento: 3,
      restrito: false,
      anonimo: false,
      partes: [
        { tipo: 'pessoa', ref: pessoas.dona_geni, papel: 'Solicitante' },
        { tipo: 'entidade', ref: entidades.amsua, papel: 'Representada' },
      ],
      interacoes: [
        {
          id: 'i347-1', tipo: 'Registro inicial', automatica: true,
          autor: usuarios.helena, data: '02/mai · 10:14',
          conteudo: 'Demanda aberta a partir de item da inbox capturado por Helena Carvalho via WhatsApp.',
        },
        {
          id: 'i347-2', tipo: 'Mudança de responsável', automatica: true,
          autor: usuarios.helena, data: '02/mai · 10:22',
          conteudo: 'Responsável atribuído: Marina Vidal (Assessoria — Mobilidade).',
        },
        {
          id: 'i347-3', tipo: 'Contato com pessoa', automatica: false, canal: 'WhatsApp',
          autor: usuarios.marina, data: '02/mai · 15:40',
          conteudo: 'Liguei para Dona Geni para entender o trecho exato e a quantidade de pontos apagados. Ela mencionou que pelo menos 9 luminárias estão sem funcionar entre a esquina da Constante Sodré até a altura do mercado Suá Fresh. Combinei vistoria presencial na sexta-feira (04/mai), 18h30, para avaliar à noite. Ela vai mobilizar 4–5 moradores para acompanhar.',
        },
        {
          id: 'i347-4', tipo: 'Reunião', automatica: false,
          autor: usuarios.marina, data: '04/mai · 19:10',
          conteudo: 'Vistoria realizada com Dona Geni e moradores. Confirmamos 11 pontos apagados (não 9). Tirei fotos e marquei coordenadas no mapa. Trecho na altura do nº 950 é o mais crítico — calçada estreita, sem iluminação por ~30m. Compromisso com moradores: ofício à SEMOB ainda nesta semana, com cópia para a EDP.',
          anexos: [
            { nome: 'vistoria-suá-04mai.pdf', tipo: 'pdf', tamanho: '2.1 MB' },
            { nome: 'mapa-pontos-apagados.png', tipo: 'img', tamanho: '780 KB' },
          ],
        },
        {
          id: 'i347-5', tipo: 'Encaminhamento externo', automatica: true,
          autor: usuarios.marina, data: '05/mai · 09:22',
          conteudo: 'Ofício OF-MPD-128/2026 enviado à SEMOB (Sec. Obras), com cópia para a EDP-ES.',
          ref: 'enc-1',
        },
        {
          id: 'i347-6', tipo: 'Anotação interna', automatica: false,
          autor: usuarios.rafael, data: '06/mai · 11:05',
          conteudo: 'Conferi a competência: troca de lâmpada em rede de iluminação pública é da SEMOB, mas a manutenção da rede (cabos, pontos novos) pode ter atravessamento com a concessionária. Vale acompanhar resposta da EDP também — se demorar, podemos protocolar requerimento de informação.',
        },
        {
          id: 'i347-7', tipo: 'Contato com pessoa', automatica: false, canal: 'WhatsApp',
          autor: usuarios.marina, data: '11/mai · 16:48',
          conteudo: 'Dei retorno parcial para Dona Geni: ofício enviado, ainda sem resposta. Prazo legal vence em 20/mai. Combinei novo contato dia 18.',
        },
        {
          id: 'i347-8', tipo: 'Reunião', automatica: false, status: 'agendada',
          autor: usuarios.marina, data: '18/mai · 14:00',
          conteudo: 'Reunião com Dona Geni e moradores para apresentar resposta da SEMOB (ou ausência dela). Local: sede da AM-Suá.',
        },
      ],
      encaminhamentos: [
        {
          id: 'enc-1', tipoDoc: 'Ofício', numero: 'OF-MPD-128/2026',
          orgao: 'Secretaria Municipal de Obras (SEMOB)',
          pessoa: 'Sr. Eduardo Galvão — Sec. de Obras',
          envio: '05/mai/2026', prazo: '20/mai/2026',
          status: 'enviado', statusLabel: 'Aguardando resposta',
          diasParaPrazo: 3,
        },
        {
          id: 'enc-2', tipoDoc: 'E-mail', numero: '',
          orgao: 'EDP Espírito Santo — Atendimento Municipal',
          envio: '05/mai/2026', prazo: '15/mai/2026',
          status: 'prazo_vencido', statusLabel: 'Prazo vencido',
          diasParaPrazo: -2,
        },
      ],
      anexos: [
        { nome: 'abaixo-assinado-87-assinaturas.pdf', tipo: 'pdf', tamanho: '4.7 MB' },
        { nome: 'vistoria-suá-04mai.pdf', tipo: 'pdf', tamanho: '2.1 MB' },
        { nome: 'mapa-pontos-apagados.png', tipo: 'img', tamanho: '780 KB' },
        { nome: 'foto-trecho-critico-noite.jpg', tipo: 'img', tamanho: '1.4 MB' },
      ],
    },

    {
      numero: 'MPD-2026-00352', slug: 'd352',
      titulo: 'Aglomeração de ônibus na Av. Reta da Penha em horário escolar',
      descricao: 'Pais e responsáveis da E.E.E.F. Almirante Barroso reclamam que os ônibus da linha 511 chegam superlotados às 7h, com crianças tendo que ir em pé. Pedem reforço da frota nos horários escolares.',
      origem: 'responsiva', canal: 'Presencial',
      status: 'aguardando_terceiros', statusLabel: 'Aguardando terceiros',
      resultado: 'pendente', prioridade: 'normal',
      coordenacao: 'Gabinete', tema: 'Mobilidade', temas: ['Mobilidade urbana', 'Educação'],
      responsavel: usuarios.marina, criadoEm: '2026-04-28', prazo: '2026-05-30',
      diasAteVencimento: 13,
      partes: [
        { tipo: 'pessoa', ref: pessoas.professor, papel: 'Solicitante' },
      ],
    },

    {
      numero: 'MPD-2026-00351', slug: 'd351',
      titulo: 'Solicitação de evento de prestação de contas no Bairro República',
      descricao: 'Proativa — agendar evento de prestação de contas do primeiro semestre.',
      origem: 'proativa', canal: 'Indicação interna',
      status: 'novo', statusLabel: 'Novo',
      resultado: 'pendente', prioridade: 'normal',
      coordenacao: 'Comunicação', tema: 'Comunicação', temas: ['Mandato', 'Comunicação'],
      responsavel: usuarios.luiza, criadoEm: '2026-05-12', prazo: '2026-06-15',
      diasAteVencimento: 29,
      partes: [],
    },

    {
      numero: 'MPD-2026-00350', slug: 'd350',
      titulo: 'Demora no agendamento de cardiologista na UBS Praia do Suá',
      descricao: 'Vários moradores relatam fila superior a 90 dias para consulta com cardiologista pela rede SUS na UBS local.',
      origem: 'responsiva', canal: 'DM Instagram',
      status: 'em_andamento', statusLabel: 'Em andamento',
      resultado: 'pendente', prioridade: 'alta',
      coordenacao: 'Gabinete', tema: 'Saúde', temas: ['Saúde'],
      responsavel: usuarios.joao, criadoEm: '2026-05-08', prazo: '2026-05-22',
      diasAteVencimento: 5,
      partes: [
        { tipo: 'pessoa', ref: pessoas.ana, papel: 'Solicitante' },
        { tipo: 'entidade', ref: entidades.ubs_pra_sua, papel: 'Afetada' },
      ],
    },

    {
      numero: 'MPD-2026-00349', slug: 'd349',
      titulo: 'Alvará vencido para comércio local em Jardim Camburi',
      descricao: 'Microempresa do Sr. Donato com alvará vencido há 4 meses; protocolo de renovação parado na PMV há 70 dias.',
      origem: 'responsiva', canal: 'Telefone',
      status: 'aguardando_terceiros', statusLabel: 'Aguardando terceiros',
      resultado: 'pendente', prioridade: 'normal',
      coordenacao: 'Jurídico', tema: 'Comércio', temas: ['Desenvolvimento econômico'],
      responsavel: usuarios.rafael, criadoEm: '2026-04-22', prazo: '2026-05-18',
      diasAteVencimento: 1,
      partes: [
        { tipo: 'pessoa', ref: pessoas.seu_donato, papel: 'Solicitante' },
      ],
    },

    {
      numero: 'MPD-2026-00348', slug: 'd348',
      titulo: 'Cooperativa de transporte alternativo pede regulamentação',
      descricao: 'Reunião com cooperativa de motoristas escolares e transporte alternativo de São Pedro.',
      origem: 'responsiva', canal: 'Presencial',
      status: 'em_andamento', statusLabel: 'Em andamento',
      resultado: 'pendente', prioridade: 'normal',
      coordenacao: 'Gabinete', tema: 'Mobilidade', temas: ['Mobilidade urbana', 'Trabalho'],
      responsavel: usuarios.marina, criadoEm: '2026-04-30', prazo: '2026-06-05',
      diasAteVencimento: 19,
      partes: [
        { tipo: 'pessoa', ref: pessoas.motorista, papel: 'Representante' },
      ],
    },

    {
      numero: 'MPD-2026-00346', slug: 'd346',
      titulo: 'Praça do Trabalhador — falta de manutenção e brinquedos quebrados',
      descricao: 'Moradores relatam descaso com a Praça do Trabalhador; brinquedos quebrados há mais de um ano.',
      origem: 'responsiva', canal: 'Redes sociais',
      status: 'concluida', statusLabel: 'Concluída',
      resultado: 'atendido_parcialmente', resultadoLabel: 'Atendido parcialmente',
      prioridade: 'normal', coordenacao: 'Gabinete', tema: 'Lazer',
      temas: ['Espaços públicos', 'Infância'],
      responsavel: usuarios.marina, criadoEm: '2026-03-10', concluidoEm: '2026-04-25',
    },

    {
      numero: 'MPD-2026-00345', slug: 'd345',
      titulo: 'Pedido de fala em audiência pública sobre IPTU',
      descricao: 'Audiência pública sobre revisão da planta genérica do IPTU. Vereador inscrito para fala.',
      origem: 'proativa', canal: 'Indicação interna',
      status: 'concluida', statusLabel: 'Concluída',
      resultado: 'atendido', resultadoLabel: 'Atendido',
      prioridade: 'normal', coordenacao: 'Gabinete', tema: 'Tributação',
      temas: ['Tributação', 'Mandato'],
      responsavel: usuarios.pedro, criadoEm: '2026-03-22', concluidoEm: '2026-04-08',
    },

    {
      numero: 'MPD-2026-00344', slug: 'd344',
      titulo: 'Vazamento de esgoto na Rua Almirante Tamandaré',
      descricao: 'Vazamento persistente há 3 semanas em rua residencial; CESAN sem retorno.',
      origem: 'responsiva', canal: 'WhatsApp',
      status: 'em_andamento', statusLabel: 'Em andamento',
      resultado: 'pendente', prioridade: 'urgente',
      coordenacao: 'Gabinete', tema: 'Saneamento', temas: ['Saneamento', 'Saúde pública'],
      responsavel: usuarios.helena, criadoEm: '2026-05-14', prazo: '2026-05-19',
      diasAteVencimento: 2,
    },

    {
      numero: 'MPD-2026-00343', slug: 'd343',
      titulo: 'Solicitação de visita à Escola Municipal Castelo Branco',
      descricao: 'Direção da escola convidou o vereador para conhecer o projeto de horta pedagógica.',
      origem: 'responsiva', canal: 'E-mail',
      status: 'novo', statusLabel: 'Novo',
      resultado: 'pendente', prioridade: 'baixa',
      coordenacao: 'Comunicação', tema: 'Educação',
      responsavel: null, criadoEm: '2026-05-15', prazo: '2026-06-10',
      diasAteVencimento: 24,
    },
  ];

  // --- Inbox (itens capturados) ---
  const inboxItens = [
    {
      id: 'ix-1',
      conteudo: 'Senhora Lúcia da Rua Coronel Schwab Filho ligou — sobrinho dela foi pego em batida de trânsito e quer entender se a CMV pode acompanhar como ouvinte na delegacia. Pediu retornar até amanhã. Tel: (27) 99812-3344.',
      autor: usuarios.helena,
      capturadoEm: 'hoje · 14:32', status: 'pendente',
    },
    {
      id: 'ix-2',
      conteudo: 'Conversa com seu Aldo (presidente da AM-Bento Ferreira): asfalto da Rua Anselmo Serrat está com várias crateras. Já reclamou direto na PMV sem retorno há 2 meses. Quer ajuda formal.',
      autor: usuarios.pedro,
      capturadoEm: 'hoje · 11:08', status: 'pendente',
    },
    {
      id: 'ix-3',
      conteudo: 'Ideia: propor moção de aplausos ao projeto de coleta seletiva da Escola Estadual Maria Ortiz — eles ganharam premiação estadual semana passada.',
      autor: usuarios.luiza,
      capturadoEm: 'ontem · 17:20', status: 'pendente',
    },
    {
      id: 'ix-4',
      conteudo: 'Verificar com Rafael: status do PL 044/2025 (acessibilidade em praças). Está parado em qual comissão?',
      autor: usuarios.pedro,
      capturadoEm: 'ontem · 09:14', status: 'pendente',
    },
    {
      id: 'ix-5',
      conteudo: 'Convite — café com lideranças do bairro Santo Antônio dia 24/mai. Já confirmar?',
      autor: usuarios.luiza,
      capturadoEm: '14/mai · 16:02', status: 'pendente',
    },
    {
      id: 'ix-6',
      conteudo: 'DM Instagram de @marcio.taxista — reclamação sobre ponto de táxi desativado na Praça Costa Pereira sem aviso.',
      autor: usuarios.helena,
      capturadoEm: '13/mai · 19:48', status: 'processado',
      virouDemanda: 'MPD-2026-00342',
    },
  ];

  return {
    usuarios, pessoas, entidades, demandas, inboxItens,
    demandaAtual: demandas[0], // a #347 é o "caso aberto"
  };
})();
