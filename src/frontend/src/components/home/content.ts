/** Conteúdo estático da página inicial (apresentação do SoftMeter). */

export interface Screenshot {
  src: string;
  width: number;
  height: number;
}

export const SCREENS = {
  login: { src: '/screens/login.jpg', width: 1920, height: 1200 },
  repos: { src: '/screens/repos.jpg', width: 1920, height: 1200 },
  dashboard: { src: '/screens/dashboard.jpg', width: 1920, height: 1785 },
  history: { src: '/screens/history.jpg', width: 1920, height: 1230 },
  report: { src: '/screens/report.jpg', width: 1920, height: 450 },
} satisfies Record<string, Screenshot>;

export const JOURNEY = [
  {
    title: 'Cadastre o repositório',
    text: 'Cole a URL de um repositório público do GitHub. O SoftMeter detecta a linguagem (Python, JavaScript ou TypeScript) automaticamente.',
  },
  {
    title: 'Execute a análise',
    text: 'O código é lido e medido por um motor de métricas. Repositórios grandes rodam em segundo plano — você não precisa esperar na tela.',
  },
  {
    title: 'Interprete o dashboard',
    text: 'Cada métrica vira um medidor com faixas de conformidade: Conforme, Condicional ou Não-Conforme, mais um resumo geral do repositório.',
  },
  {
    title: 'Acompanhe e compartilhe',
    text: 'Veja a evolução a cada nova análise, identifique tendências e gere um relatório técnico em PDF para apresentar.',
  },
];

/** Descrições didáticas por métrica (chaves iguais às de metricsCatalog). */
export const METRIC_INFO: Record<string, { summary: string; reading: string }> = {
  complexidade_ciclomatica: {
    summary: 'Conta os caminhos de decisão independentes de cada função.',
    reading: 'Quanto menor, mais fácil de entender e de testar.',
  },
  loc: {
    summary: 'Mede a quantidade média de linhas de código por função.',
    reading: 'Funções curtas tendem a ter uma única responsabilidade.',
  },
  indice_manutenibilidade: {
    summary: 'Índice composto de 0 a 100 que estima o esforço para manter o código.',
    reading: 'Quanto maior, mais sustentável é a base de código.',
  },
  cobertura_testes: {
    summary: 'Percentual do código exercitado pelos testes automatizados.',
    reading: 'Lida do resultado do CI do repositório — o SoftMeter nunca executa o código analisado.',
  },
  acoplamento: {
    summary: 'Instabilidade entre 0 e 1, calculada pelas dependências entre módulos.',
    reading: 'Quanto menor, mais isolado e estável é o módulo.',
  },
  score_duplicacao: {
    summary: 'Percentual de trechos de código repetidos no projeto.',
    reading: 'Duplicação alta multiplica o custo de cada correção.',
  },
};

export const DIFFERENTIALS = [
  {
    title: 'Sem executar seu código',
    text: 'A análise é estática: o SoftMeter lê o código-fonte, mas nunca instala dependências nem roda comandos do repositório.',
  },
  {
    title: 'Conformidade objetiva',
    text: 'Cada métrica é comparada a limiares definidos, como um instrumento de medição calibrado — sem opinião, só dados.',
  },
  {
    title: 'Histórico e tendências',
    text: 'Cada análise fica registrada. Veja se a qualidade está melhorando, piorando ou estável ao longo do tempo.',
  },
  {
    title: 'Relatório em PDF',
    text: 'Gere um relatório técnico de qualquer análise concluída, pronto para anexar a uma entrega ou apresentação.',
  },
];

export interface TutorialSlide {
  title: string;
  text: string;
  image: Screenshot;
  alt: string;
  fit?: 'top' | 'center';
}

export const TUTORIAL: TutorialSlide[] = [
  {
    title: 'Entre ou crie sua conta',
    text: 'Clique em “Criar conta” com seu e-mail e uma senha de pelo menos 8 caracteres. Se já tem conta, use “Entrar”.',
    image: SCREENS.login,
    alt: 'Tela de login do SoftMeter com campos de e-mail e senha',
  },
  {
    title: 'Cadastre um repositório',
    text: 'Na tela de Repositórios, cole a URL pública do GitHub (por exemplo, https://github.com/pallets/click) e clique em “Cadastrar”.',
    image: SCREENS.repos,
    alt: 'Tela de repositórios com o campo de URL do GitHub e a lista de repositórios cadastrados',
  },
  {
    title: 'Execute a análise',
    text: 'No card do repositório, clique em “Executar análise”. Quando o selo mudar para “concluida”, o botão “Ver dashboard” aparece.',
    image: SCREENS.repos,
    alt: 'Card de repositório com os botões Ver dashboard, Executar análise e Remover',
  },
  {
    title: 'Leia o dashboard de conformidade',
    text: 'O banner mostra a conformidade geral; os contadores resumem as métricas por status e cada medidor indica o valor medido e sua faixa.',
    image: SCREENS.dashboard,
    alt: 'Dashboard de conformidade com seis medidores de métricas de qualidade',
  },
  {
    title: 'Acompanhe a evolução',
    text: 'Em “Ver histórico e tendências”, escolha uma métrica para ver como ela evoluiu a cada análise e se a tendência é de melhora, piora ou estabilidade.',
    image: SCREENS.history,
    alt: 'Gráfico de histórico e tendência de uma métrica ao longo das análises',
  },
  {
    title: 'Gere o relatório em PDF',
    text: 'No dashboard, clique em “Gerar relatório PDF” para baixar um relatório técnico da análise, pronto para compartilhar.',
    image: SCREENS.report,
    alt: 'Banner do dashboard destacando o botão Gerar relatório PDF',
    fit: 'center',
  },
];

export const FAQ = [
  {
    q: 'O SoftMeter executa o código do meu repositório?',
    a: 'Não. A análise é estática: o código-fonte é lido e medido, mas nada é instalado ou executado. A cobertura de testes vem do resultado que o próprio CI do repositório já publicou.',
  },
  {
    q: 'Quais repositórios posso analisar?',
    a: 'Repositórios públicos do GitHub escritos em Python, JavaScript ou TypeScript. Repositórios privados não são suportados.',
  },
  {
    q: 'Por que a Cobertura de Testes aparece como “Não disponível”?',
    a: 'Ela só é medida quando o repositório publica um relatório de cobertura (por exemplo, pelo GitHub Actions). Sem esse artefato, a métrica é marcada como indisponível e não entra no resultado geral.',
  },
  {
    q: 'Quanto tempo leva uma análise?',
    a: 'Repositórios pequenos terminam em poucos segundos. Os maiores rodam em segundo plano e o status é atualizado quando concluírem.',
  },
  {
    q: 'O que significam Conforme, Condicional e Não-Conforme?',
    a: 'São as faixas de cada medidor: Conforme está dentro do esperado, Condicional pede atenção e Não-Conforme indica que o valor passou do limite aceitável para aquela métrica.',
  },
  {
    q: 'O que é o SoftMeter?',
    a: 'Um projeto de TCC que aplica conceitos de metrologia — medir, comparar com um padrão e declarar conformidade — à qualidade de software.',
  },
];
