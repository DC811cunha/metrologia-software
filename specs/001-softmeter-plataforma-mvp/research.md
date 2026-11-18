# Research: SoftMeter — Plataforma de Metrologia de Qualidade de Software

**Feature**: 001-softmeter-plataforma-mvp | **Date**: 2026-06-24 | **Atualizado**: 2026-11-18 (itens 13 a 18 e notas de revisão nos itens 1, 3 a 7, 9 e 11)

Este documento resolve as decisões técnicas necessárias para a Phase 1, derivadas da stack
definida em ADR-003 e dos requisitos funcionais do `spec.md`.

## 1. Ingestão do código-fonte do repositório GitHub

- **Decision**: Baixar o conteúdo do repositório via o endpoint público de arquivo compactado do
  GitHub (`GET /repos/{owner}/{repo}/zipball/{ref}`), extrair em um diretório de trabalho
  temporário isolado por análise, processar, e remover o diretório ao final (sucesso ou falha).
  *(Atualização, ADR-009 e ADR-013: o download é em streaming com tetos de tamanho, de conteúdo extraído e de
  número de arquivos; segue redirecionamentos do GitHub; erros de rede/cota viram erros tipados.)*
- **Rationale**: Não exige o binário `git` no worker, funciona com requisições HTTP simples
  (`httpx`), e entrega todo o código de uma vez (mais rápido que a API de Conteúdo arquivo-a-
  arquivo para repositórios com muitos arquivos), favorecendo o orçamento de 10s do Princípio IV.
- **Alternatives considered**: (a) `git clone --depth 1` — exigiria o binário Git instalado no
  worker e tratamento de autenticação SSH/HTTPS; sem ganho relevante para repositórios públicos.
  (b) API de Conteúdo do GitHub arquivo por arquivo — número de requisições proporcional à
  quantidade de arquivos, mais lento e sujeito a limites de taxa mais cedo.

## 2. Detecção de linguagem do repositório (FR-002)

- **Decision**: Usar o endpoint `GET /repos/{owner}/{repo}/languages` do GitHub (retorna bytes
  por linguagem) no momento do cadastro; aceitar o repositório apenas se Python e/ou
  JavaScript/TypeScript estiverem entre as linguagens detectadas, e analisar apenas os arquivos
  dessas linguagens (demais arquivos são ignorados pelo motor de métricas).
- **Rationale**: É o mesmo dado que o GitHub usa para exibir a barra de linguagens no repositório,
  evitando heurísticas próprias de detecção de linguagem.
- **Alternatives considered**: Detectar linguagem apenas por extensão de arquivo após o download
  — redundante com um dado que o GitHub já expõe de forma mais confiável (ex.: arquivos gerados,
  vendor/, etc. já são excluídos pelo GitHub Linguist).

## 3. Complexidade Ciclomática, LOC e Índice de Manutenibilidade

- **Decision**: Para arquivos Python, usar **Radon** diretamente (já implementa as fórmulas
  publicadas de McCabe (1976) para Complexidade Ciclomática e de Coleman et al. (1994) para o
  Índice de Manutenibilidade, com LOC contado por SLOC lógico). Para arquivos JavaScript/
  TypeScript, usar **tree-sitter** (bindings Python `tree-sitter`, `tree-sitter-javascript` e
  `tree-sitter-typescript`) para obter a AST
  e aplicar exatamente a mesma fórmula documentada no catálogo de métricas (mesma definição de
  McCabe para nós de decisão; mesma fórmula de Coleman et al. para o Índice de Manutenibilidade),
  garantindo que a definição da métrica seja idêntica entre as duas linguagens suportadas
  (consistência exigida pelo Princípio V).
- **Rationale**: Radon é a biblioteca Python madura e testada para essas três métricas; não há
  biblioteca equivalente fora do ecossistema JS/Node para JS/TS, e introduzir um runtime Node no
  backend Python contradiz o ADR-003. `tree-sitter` permite reimplementar a mesma fórmula
  documentada sem depender de um runtime JS.
- **Alternatives considered**: Invocar uma ferramenta Node (ex.: `escomplex`) via subprocesso a
  partir do backend Python — adicionaria uma segunda runtime/dependência de sistema operacional
  ao Docker image, contrariando a simplicidade pretendida pelo ADR-003.
- **Atualização (ADR-015)**: a média do Índice de Manutenibilidade do repositório é **ponderada pelo SLOC** de cada
  arquivo (convenção do Visual Studio): um arquivo de uma linha não pesa o mesmo que um módulo de 500. Medido em
  repositórios reais, a média simples → ponderada foi de 60,5 → 32,8 (`pallets/click`) e 51,8 → 29,8 (o próprio
  SoftMeter); os limites do MI por arquivo não mudaram.
- **Atualização (ADR-010)**: LOC passou a ser a contagem de linhas **físicas** com código, igual em Python
  (`sloc` do Radon, que alimenta também o Índice de Manutenibilidade) e em JS/TS (comentários identificados
  pela AST do tree-sitter). Arquivos de teste, dependências e arquivos gerados/minificados ficam fora (ADR-011).

## 4. Acoplamento

- **Decision**: Métrica de **Instabilidade de Módulo** (`I = Ce / (Ce + Ca)`), onde `Ce`
  (Acoplamento de Saída) é o número de módulos/arquivos distintos importados por um módulo e `Ca`
  (Acoplamento de Entrada) é o número de módulos distintos que importam aquele módulo, calculada
  por arquivo e agregada por média no repositório. Implementada pelo parser AST próprio (extração
  de declarações `import`/`from...import` em Python e `import`/`require` em JS/TS via
  tree-sitter).
- **Rationale**: É uma métrica de acoplamento com definição formal e fonte bibliográfica
  amplamente citada (Robert C. Martin, *Agile Software Development: Principles, Patterns, and
  Practices*, 2002), aplicável de forma equivalente a ambas as linguagens suportadas via grafo de
  imports — exatamente o que o Princípio V exige (fórmula + fonte + limites).
  *(Atualização, ADR-010 e ADR-012: os imports Python são casados com o **sufixo do caminho** dos módulos
  (qualquer layout) e ignorados se ambíguos; em JS/TS valem `paths`/`baseUrl` do `tsconfig`/`jsconfig` mais
  próximo, seguindo `extends`. Sem nenhum import interno resolvido, o resultado é "Não disponível" em vez
  de um falso `0,0`. Desde o ADR-015 isso vale também para um repositório de um único módulo: `I = Ce/(Ce+Ca)` é
  0/0, indefinido.)*
- **Alternatives considered**: CBO (Coupling Between Objects, Chidamber & Kemerer, 1994) — mais
  apropriado a paradigma orientado a objetos por classe; rejeitado porque parte do código-alvo
  (especialmente JS funcional) não é estruturado em classes, tornando a métrica inconsistente
  entre repositórios.

## 5. Score de Duplicação

- **Decision**: Detecção de clones Tipo-1/Tipo-2 por *shingling* de blocos de tokens normalizados
  (identificadores e literais substituídos por placeholders), com janela mínima configurável
  (ex.: 6 linhas), usando a mesma AST do tree-sitter para tokenizar. Score = percentual de linhas
  de código duplicadas em relação ao total de linhas analisadas. *(Atualização, ADR-010: imports não
  contam; a janela precisa de ao menos 4 linhas normalizadas distintas; janelas sobrepostas do mesmo arquivo
  não casam entre si.)*
- **Rationale**: É a mesma abordagem (normalização + comparação de blocos) usada por ferramentas
  de mercado de detecção de duplicação (ex.: a métrica de "duplicated lines density" do
  SonarQube), com formato comparável e fonte documentável.
- **Alternatives considered**: Comparação textual exata linha a linha — não detecta clones Tipo-2
  (renomeação de variáveis), produzindo um score artificialmente baixo.

## 6. Cobertura de Testes (decisão confirmada com o usuário)

- **Decision**: O SoftMeter **não executa** a suíte de testes do repositório analisado. Em vez
  disso, procura artefatos de cobertura já publicados no repositório (`coverage.xml`, `lcov.info`,
  `.coverage`, badge do Codecov/Coveralls referenciado no `README`) e extrai o percentual relatado.
  Quando nenhum artefato é encontrado, a métrica é marcada como **"Não disponível"** para aquela
  análise e é excluída do índice agregado de conformidade (em vez de contar como Não-Conforme).
- **Rationale**: Executar código de terceiros arbitrário (instalar dependências e correr a suíte
  de testes de um repositório público desconhecido) é uma superfície de execução de código
  arbitrário que o projeto explicitamente decidiu não assumir nesta versão, e dificilmente caberia
  no orçamento de 10s do Princípio IV. Ler artefatos estáticos já publicados é seguro e rápido.
- **Alternatives considered**: Executar testes em sandbox isolado (rejeitado por risco de
  segurança e custo de infraestrutura); métrica proxy estática de razão teste/código (rejeitado
  por divergir do nome e do significado de "Cobertura de Testes" definidos no spec).
- **Atualização (16/09/2026, ver ADR-004)**: adicionada uma fonte antes das listadas acima — o
  artifact de cobertura mais recente publicado pelo GitHub Actions do próprio repositório
  analisado (ex.: `backend-coverage`, `frontend-coverage`), baixado sem executar nada. Motivo: a
  maioria dos repositórios públicos não versiona artefato de build (é o próprio caso do
  SoftMeter), o que deixava a métrica quase sempre "Não disponível" na prática. A decisão de
  nunca executar código do repositório analisado permanece intacta.
- **Atualização (ADR-011 e ADR-012)**: a busca por `coverage.xml`/`lcov.info` ignora diretórios de
  dependências e é determinística (caminho mais raso primeiro, depois alfabético); relatórios múltiplos são
  combinados por soma de linhas. Em monorepos, **todos** os artifacts de cobertura do run de CI mais recente
  (até `MAX_COVERAGE_ARTIFACTS`) são baixados e combinados, e o XML é lido com `defusedxml` (ADR-009).

## 7. Processamento assíncrono e orçamento de 10 segundos (Princípio IV)

- **Decision**: A requisição de análise consulta o tamanho do repositório na API do GitHub
  (`size`, em KB). Se estiver dentro de um limite configurável (`sync_analysis_size_limit_kb`,
  padrão 5000 KB), as 6 métricas são calculadas de forma síncrona e o resultado é retornado
  diretamente (HTTP 201). Caso o repositório seja maior, a tarefa é despachada para uma fila
  Celery/Redis e o endpoint retorna imediatamente (HTTP 202) um identificador de análise com
  status "processando"; o frontend faz polling (a cada 2 s) até a conclusão. *(Redação original:
  heurística por número de arquivos elegíveis e orçamento de ~8 s; a implementação adotou o
  tamanho informado pelo GitHub, que é conhecido antes de baixar qualquer código.)*
  *(Atualização, ADR-009: acima de `max_repo_size_kb` — 200 MB — a análise é recusada com HTTP 422; a análise
  síncrona tem prazo cooperativo de 300 s e o worker Celery tem `soft_time_limit`/`time_limit` por cima.
  Se a fila estiver fora do ar, a resposta é HTTP 503 e a análise fica `falhou`, nunca presa.)*
  *(Atualização, ADR-008: só uma análise em andamento por repositório (índice único parcial; o segundo pedido recebe
  409) e, com `MAX_CONCURRENT_SYNC_ANALYSES` análises síncronas em curso no processo, a nova vai para a fila (202).
  Análises que passam de `STALE_ANALYSIS_AFTER_S` sem terminar viram `falhou` ao serem listadas ou lidas.)*
- **Rationale**: Atende ao Princípio IV (resultado em até 10s para o caso padrão) sem impor um
  hard timeout abrupto que descartaria análises de repositórios maiores — a degradação graciosa é
  explicitamente exigida pela constituição.
- **Alternatives considered**: Sempre assíncrono (mais simples de implementar, mas penaliza a
  experiência do caso comum de repositórios pequenos, que é a maioria no contexto de um TCC).

## 8. Geração de relatório PDF

- **Decision**: ReportLab para montar o PDF diretamente no backend, com um template programático
  que inclui: identificação do repositório, data da análise, e para cada métrica — valor medido,
  fórmula, fonte bibliográfica e limites de especificação (lidos do catálogo de métricas em
  `data-model.md`), e gráfico de tendência (quando solicitado para o histórico).
- **Rationale**: Biblioteca madura, sem dependências de sistema externas (ex.: não exige um
  navegador headless), adequada a um PDF estruturado/tabular como o exigido pelo FR-009.
- **Alternatives considered**: Renderizar HTML e converter via um navegador headless (ex.:
  Playwright/Chromium) — mais pesado para um documento essencialmente tabular, e adicionaria
  outra dependência de runtime ao container do backend.

## 9. Autenticação

- **Decision**: JWT de acesso de curta duração (ex.: 15 min) + refresh token de longa duração
  (ex.: 7 dias), ambos assinados pelo backend; senhas hasheadas com bcrypt. Refresh token
  armazenado como cookie HTTPOnly; access token usado no header `Authorization: Bearer`.
  *(Atualização, ADR-006: o refresh token vai **somente** no cookie (nunca no corpo); ambos os tokens
  carregam a `token_version` do usuário, que sobe no logout e no reset de senha e revoga a sessão na hora —
  o refresh continua sem estado e sem tabela de sessões. O logout é idempotente e identifica a sessão pelo
  cookie do refresh, para funcionar mesmo com o access token expirado.)*
- **Rationale**: Padrão de mercado para APIs FastAPI stateless, equilibra segurança (token de
  acesso de vida curta) e experiência do usuário (refresh evita logins repetidos).
- **Alternatives considered**: Sessão baseada em cookie no servidor (stateful) — exigiria estado
  de sessão compartilhado caso o backend escale horizontalmente; descartado por não haver
  exigência de escala nesta versão, mas JWT mantém a opção aberta sem custo adicional.

## 10. Testes E2E

- **Decision**: Playwright, cobrindo os fluxos críticos através da UI real do frontend Vite/React.
  *(Redação original: apenas US1 e US2. Implementado: um arquivo por user story — US1 a US5 — mais
  a página inicial pública e a confirmação de exclusão de repositório; 15 cenários. A suíte roda localmente,
  contra a aplicação completa, e não faz parte do job de CI.)*
- **Rationale**: Suporta TypeScript nativamente, integra-se bem a um frontend Vite, e é a opção
  mais usada atualmente para E2E em aplicações React.
- **Alternatives considered**: Cypress — também viável; Playwright foi preferido por suporte
  nativo a múltiplos navegadores e melhor desempenho em pipelines de CI.

## 11. Recuperação de senha (pós-MVP, 16/09/2026)

- **Decision**: Token aleatório de 32 bytes enviado por e-mail, guardado apenas como hash SHA-256,
  de uso único e com expiração de 60 min; e-mail transacional via Resend (API HTTP direta), com
  fallback de log quando não há `RESEND_API_KEY`; envio em task Celery para não vazar informação
  por tempo de resposta. Registro completo, alternativas e limitações (sandbox sem domínio
  próprio) em `docs/adr/ADR-005-recuperacao-de-senha-via-email.md`.

  *(Atualização, ADR-005: o endpoint não consulta o banco — só enfileira `request_password_reset` — e o worker grava o
  token e envia o e-mail, com no máximo 3 pedidos por conta por hora. Medido: ~174 ms × ~151 ms antes, ~147 ms ×
  ~150 ms depois.)*

## 12. Camada de estilo do frontend (Tailwind desde o MVP; tema escuro em 03/11/2026)

- **Decision**: Tailwind CSS 3 sobre React/Vite (adotado no MVP), com — a partir do redesign de
  03/11/2026 — tokens semânticos de tema (`canvas`,
  `surface`, `line`, `fg*`, `glow`) em variáveis CSS e tema escuro azul-navy como padrão. Sem novas
  dependências de componentes; textos, labels e estruturas usados pelos testes foram preservados no
  redesign.
- **Rationale**: concentra o tema em um único lugar (um tema claro opcional fica viável) e mantém
  os gauges, a semântica de cor de conformidade (verde/âmbar/vermelho — distinta do azul da marca)
  e a acessibilidade (foco visível, `prefers-reduced-motion`, status nunca só por cor).

## 13. Limites de custo e de requisições (pós-MVP, 08/11/2026)

- **Decision**: tetos configuráveis para tudo que o usuário pode forçar o servidor a baixar ou processar
  (tamanho do repositório, download, conteúdo extraído, número de arquivos, arquivo-fonte, artifact de
  cobertura, tempo de análise — ADR-009) e rate limit por IP, em memória ou Redis (ADR-008); com
  `ENVIRONMENT=production`, a API se recusa a iniciar com configuração insegura (ADR-007).
- **Rationale**: o SoftMeter processa conteúdo de terceiros em um serviço público; falhar alto e cedo é mais
  seguro que degradar em silêncio.
- **Alternatives considered**: rate limit só em memória (não vale entre réplicas); pré-hash da senha para
  aceitar senhas longas (mudaria todos os hashes — ADR-006).

## 14. Erros temporários do GitHub (pós-MVP, 08/11/2026)

- **Decision**: classificar toda resposta de erro do GitHub em três famílias — acesso negado (403/404/451),
  cota esgotada (429 ou 403 com sinal de limite, com `Retry-After`) e indisponibilidade (5xx/rede). Só a
  primeira marca o repositório como `inacessivel`; as outras falham a análise com o motivo e deixam o
  repositório ativo. Não há bloqueio antecipado: a análise sempre consulta o GitHub (ADR-013).

## 15. Identidade do repositório (pós-MVP, 13/11/2026)

- **Decision**: guardar o `id` numérico do GitHub (`repositories.github_id`) na primeira análise e, a cada
  análise, atualizar `url`/`owner_nome` para o nome canônico e barrar a análise se o id mudou (nome
  reaproveitado por outro repositório). Duplicatas não são fundidas automaticamente (ADR-014).

## 16. Escopo da medição (pós-MVP, 08/11/2026)

- **Decision**: medir apenas código de produção — testes, dependências e arquivos gerados/minificados ficam
  de fora das métricas de código — e mostrar isso ao usuário no dashboard e no PDF (`SCOPE_NOTE`, mantido em
  dois lugares: `analysis/metrics_catalog.py` e `frontend/src/metricsCatalog.ts`). Ver ADR-011 e ADR-012.

## 17. Concorrência de análises e análises perdidas (pós-MVP, 18/11/2026)

- **Decision**: uma análise `pendente`/`processando` por repositório, garantida por um **índice único parcial** no banco
  (sem corrida) mais uma checagem prévia que devolve 409; teto de análises síncronas por processo, com a fila como
  válvula de escape; e encerramento, por tempo, das análises que nunca terminam — feito nas próprias consultas de
  listagem/leitura, sem processo agendado (ADR-008, ADR-013).
- **Alternatives considered**: tornar toda análise assíncrona (deixado para o deploy, pois muda a experiência de uso);
  `acks_late` no Celery (reexecutaria tarefas e duplicaria análises); um "reaper" agendado (mais uma peça no deploy).

## 18. Dependências e build reprodutível (pós-MVP, 18/11/2026)

- **Decision**: `src/backend/requirements.txt` fixa todas as versões do backend (Docker e CI usam `-c`); `npm ci` no CI;
  Dependabot semanal e workflow `audit.yml` (`pip-audit` + `npm audit`, fora dos checks obrigatórios); imagem de produção
  sem extras de teste, sem `--reload` e sem root; PDFs em volume nomeado. O frontend está em `react-router` 7, `vite` 7 e
  `@typescript-eslint` 8, com `npm audit` zerado (ADR-007).
- **Rationale**: builds que mudam sozinhos tornam falhas irreproduzíveis; vulnerabilidades devem aparecer sem esperar uma
  revisão manual.

## Resumo das decisões

| # | Tópico | Decisão |
|---|---|---|
| 1 | Ingestão de código | Download de zipball via API do GitHub |
| 2 | Detecção de linguagem | Endpoint `languages` do GitHub |
| 3 | Complexidade/LOC/MI | Radon (Python) + tree-sitter com mesma fórmula (JS/TS) |
| 4 | Acoplamento | Instabilidade de Módulo (Martin, 2002) via grafo de imports |
| 5 | Duplicação | Shingling de tokens normalizados (estilo SonarQube) |
| 6 | Cobertura de Testes | Artifact do GitHub Actions (ADR-004) → artefatos versionados; "Não disponível" se ausente |
| 7 | Performance/assincronia | Síncrono até o limite de tamanho (5000 KB); acima, Celery+Redis com polling |
| 8 | Relatório PDF | ReportLab |
| 9 | Autenticação | JWT (access curto + refresh longo) + bcrypt |
| 10 | E2E | Playwright (US1–US5, página inicial e exclusão de repositório) |
| 11 | Recuperação de senha *(pós-MVP)* | Token de uso único com hash SHA-256 + e-mail via Resend (ADR-005) |
| 12 | Camada de estilo do frontend | Tailwind CSS 3 (MVP); tokens de tema em variáveis CSS e tema escuro *(pós-MVP)* |
| 13 | Limites de custo e de requisições *(pós-MVP)* | Tetos configuráveis, rate limit por IP (memória/Redis), produção recusa configuração insegura (ADR-007/008/009) |
| 14 | Erros temporários do GitHub *(pós-MVP)* | Erros tipados; cota/indisponibilidade falham a análise sem bloquear o repositório (ADR-013) |
| 15 | Identidade do repositório *(pós-MVP)* | `github_id` + nome canônico; nome reaproveitado barra a análise (ADR-014) |
| 16 | Escopo da medição *(pós-MVP)* | Só código de produção, com nota visível no dashboard e no PDF; pastas ambíguas julgadas por contexto (ADR-011/012/015) |
| 17 | Concorrência de análises *(pós-MVP)* | Uma por repositório (índice único parcial), teto síncrono com fila, análises perdidas viram falha (ADR-008/013) |
| 18 | Dependências e build *(pós-MVP)* | Versões fixas, Dependabot, auditoria, imagem de produção não-root, volume dos PDFs (ADR-007) |

Nenhum item de Technical Context permanece como NEEDS CLARIFICATION após esta pesquisa.
