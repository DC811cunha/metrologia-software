<!--
Sync Impact Report
==================
Version change: 1.0.0 → 2.0.0 (MAJOR)
Rationale: ADR-003 (docs/adr/ADR-003-stack-backend-fastapi.md) replaces the backend defined in
ADR-001 (Node.js + TypeScript + Express) with FastAPI + Python 3.12 + Celery/Redis, to use the
mature Python static-analysis ecosystem (Radon) as the core of the metric engine. This redefines
the binding technology stack established in v1.0.0, which is an incompatible governance change
for any plan/PR that assumed the Node.js stack — hence MAJOR.

Modified principles:
- I. Qualidade de Código com Cobertura Mínima de 80% — wording generalized from a Jest-only,
  Node-path-specific requirement to a per-language coverage tool requirement (pytest-cov for the
  Python backend, Jest for the React frontend), so the principle does not need a new amendment on
  every future stack change.
- II. Disciplina de Testes em Múltiplas Camadas — wording generalized from Node-specific
  directory names (`controllers/`, `routes/`, `repositories/`) to layer descriptions (camada de
  entrada HTTP, camada de regras de negócio, camada de persistência) that apply equally to the
  FastAPI structure.

Principles added/removed: none (I-V unchanged in substance, only de-coupled from Node-specific
wording; see modifications above)

Sections modified:
- Restrições Tecnológicas e de Stack — full replacement: backend FastAPI/Python 3.12, PostgreSQL
  16, Celery+Redis, Radon + parser AST próprio, React 18 + TypeScript + Vite, Recharts, ReportLab,
  JWT (access+refresh) + bcrypt, Docker Compose, GitHub Actions. Node.js/Express removed as
  binding stack per ADR-003.

Templates requiring updates:
- ✅ .specify/templates/plan-template.md — generic "[Gates determined based on constitution
  file]" placeholder still defers to this document; no edit needed.
- ✅ .specify/templates/spec-template.md — generic, technology-agnostic; no changes required.
- ✅ .specify/templates/tasks-template.md — generic task categorization unaffected by stack
  change.
- ⚠ docs/adr/ADR-001-stack-tecnologica.md is superseded for the backend layer by ADR-003; ADR-001
  is kept as historical record (status not edited) and ADR-003 cross-references it.

Follow-up TODOs:
- TODO(METRICS_CATALOG_LOCATION): exact path for the metrics catalog required by Principle V
  (e.g., docs/metrics/) should be formalized in the plan/data-model of feature
  001-softmeter-plataforma-mvp.
-->

# SoftMeter Constitution

## Core Principles

### I. Qualidade de Código com Cobertura Mínima de 80%

Todo código de produção (backend `src/backend/` e frontend `src/frontend/src/`) DEVE manter
cobertura automatizada de testes igual ou superior a 80%, medida em linhas e branches pela
ferramenta de cobertura adequada à linguagem de cada camada (`pytest-cov` no backend Python,
relatórios de cobertura do Jest no frontend). Pipelines de CI DEVEM bloquear merge de Pull
Requests que reduzam a cobertura abaixo do limiar vigente ou que introduzam regressão de
cobertura em arquivos já cobertos. Lint e checagem de tipos (`mypy`/`ruff` no backend,
TypeScript `strict` no frontend) DEVEM passar sem erros antes de qualquer merge; alertas de
análise estática (SonarCloud ou equivalente) classificados como bloqueantes DEVEM ser
resolvidos antes do merge.

**Rationale**: Assim como uma peça fora de tolerância dimensional é refugada na indústria,
código sem cobertura mínima comprovada não pode ser aceito como "conforme". O limiar de 80%
é o critério objetivo e verificável que substitui a afirmação subjetiva de que o software
"está pronto".

### II. Disciplina de Testes em Múltiplas Camadas (Unit, Integração e E2E)

Toda funcionalidade nova ou alterada DEVE ser validada nas três camadas de teste do projeto:

- **Testes unitários**: cobrem regras de negócio isoladas na camada de serviços/regras de
  negócio, sem I/O real (banco de dados, rede, sistema de arquivos mockados).
- **Testes de integração**: validam contratos entre camadas reais — camada de entrada HTTP
  (rotas/endpoints) + camada de regras de negócio + camada de persistência — contra um banco de
  dados de teste, e chamadas reais à API do GitHub via fixtures/stubs controlados.
- **Testes E2E**: validam os fluxos críticos de ponta a ponta (cadastro de repositório GitHub,
  execução de análise automática, visualização do dashboard com gauges metrológicos) através
  da interface real do frontend.

Testes DEVEM ser escritos antes ou junto da implementação (nunca adicionados apenas para
"tapar buraco" de cobertura) e DEVEM falhar antes da implementação corrigi-los quando praticável.
A suíte completa (unit + integração + E2E) DEVE executar em CI a cada Pull Request; falha em
qualquer camada bloqueia o merge.

**Rationale**: Uma única camada de teste é equivalente a uma única medição sem repetição —
não garante confiabilidade. A redundância entre camadas (unitário, integração, E2E) é o
equivalente metrológico a medições repetidas e calibração cruzada de instrumentos.

### III. Consistência de Interface Metrológica

Toda visualização de métrica (Complexidade Ciclomática, LOC, Índice de Manutenibilidade,
Cobertura de Testes, Acoplamento e quaisquer métricas futuras) DEVE usar a mesma linguagem
visual de gauge metrológico: valor medido, zona de tolerância (faixas verde/amarelo/vermelho)
e valor nominal/alvo exibidos de forma consistente. As faixas de classificação DEVEM seguir o
mesmo critério usado no Laudo de Conformidade do projeto (≥ 90% Conforme, 70–89% Condicional,
< 70% Não-Conforme, conforme definido no README), salvo quando a métrica tiver limites de
referência próprios documentados (ver Princípio V) — nesse caso os limites próprios prevalecem,
mas a codificação de cores e o layout do gauge permanecem os mesmos.

Novos tipos de métrica DEVEM reutilizar os componentes de dashboard já existentes
(`src/frontend/src/components/`); a criação de um componente de visualização ad hoc para uma
métrica individual exige justificativa documentada (ver Complexity Tracking no plano da feature).

**Rationale**: Em metrologia industrial, instrumentos calibrados de fabricantes diferentes
ainda apresentam leituras em formato comparável (unidade, tolerância, desvio). O dashboard do
SoftMeter deve oferecer a mesma previsibilidade visual para que desenvolvedores comparem
métricas distintas sem precisar reaprender a interface a cada novo indicador.

### IV. Performance da Análise (< 10 segundos)

A execução de uma análise automática de um repositório cadastrado (coleta de Complexidade
Ciclomática, LOC, Índice de Manutenibilidade, Cobertura de Testes e Acoplamento) DEVE retornar
e renderizar o resultado inicial ao usuário em até 10 segundos (p95) para o caso de uso padrão
do projeto (repositório de porte pequeno a médio, conforme escopo do TCC). Quando o volume do
repositório analisado ultrapassar o que é processável dentro desse limite, o sistema DEVE
degradar de forma graciosa: iniciar a análise de forma assíncrona, exibir indicador de progresso
e notificar o usuário na conclusão, em vez de bloquear a interface ou falhar silenciosamente.
Toda feature que introduza ou modifique o pipeline de análise DEVE incluir um teste de
performance (medição de tempo de execução) nos critérios de aceite.

**Rationale**: Uma medição que demora demais perde valor para quem precisa de feedback rápido
durante o desenvolvimento — o equivalente a um instrumento de medição industrial lento demais
para a linha de produção. Dez segundos é o limite que mantém a análise útil dentro do fluxo de
trabalho do desenvolvedor.

### V. Rastreabilidade Metrológica das Métricas (NON-NEGOTIABLE)

Nenhuma métrica PODE ser exibida em um dashboard, gauge ou Laudo de Conformidade sem que exista,
previamente, uma entrada formal no catálogo de métricas do projeto contendo, no mínimo:

1. **Nome e unidade de medida** da métrica;
2. **Fórmula de cálculo** completa e não ambígua;
3. **Fonte bibliográfica** que sustenta a definição e a fórmula (norma, paper, livro — por
   exemplo VIM/INMETRO, ISO/IEC 25010, McCabe (1976) para Complexidade Ciclomática, Halstead ou
   Coleman et al. (1994) para Índice de Manutenibilidade, conforme aplicável);
4. **Limites de referência** (valor nominal, limite superior e limite inferior de tolerância) e
   a justificativa desses limites.

Esta regra é "definição-antes-de-exibição": a entrada no catálogo DEVE existir e estar revisada
antes que a métrica correspondente seja implementada na interface. Qualquer alteração posterior
na fórmula ou nos limites de referência de uma métrica já publicada DEVE ser versionada e
registrada no changelog do catálogo de métricas, preservando o histórico de qual fórmula/limite
estava em vigor em cada período.

**Rationale**: Este é o princípio fundador do projeto. A metrologia industrial não aceita uma
medição sem rastreabilidade ao padrão e ao instrumento que a calibrou; o SoftMeter aplica a
mesma exigência ao software — sem definição formal, fórmula, fonte e limites, uma métrica é
apenas um número sem significado verificável.

## Restrições Tecnológicas e de Stack

A stack tecnológica abaixo, definida pelo ADR-003 (`docs/adr/ADR-003-stack-backend-fastapi.md`,
que substitui o backend originalmente definido no ADR-001), é vinculante para todo
desenvolvimento, salvo decisão registrada em novo ADR (`docs/adr/`):

- **Backend / API**: FastAPI + Python 3.12, em `src/backend/`.
- **Banco de dados**: PostgreSQL 16.
- **Processamento assíncrono**: Celery + Redis, para execuções de análise que excedam o
  orçamento de tempo síncrono do Princípio IV.
- **Motor de cálculo de métricas**: Radon (Complexidade Ciclomática, LOC, Índice de
  Manutenibilidade) + parser AST próprio (Acoplamento, Score de Duplicação).
- **Frontend**: React 18 + TypeScript, com Vite como build tool, em `src/frontend/`.
- **Visualização/gráficos**: Recharts, reutilizado pelos componentes de gauge do Princípio III.
- **Geração de relatórios**: ReportLab, executado no backend, para os PDFs do Princípio V.
- **Autenticação**: JWT (access token + refresh token) com hashing de senha via bcrypt.
- **Testes**: `pytest` + `pytest-cov` no backend, Jest + Testing Library no frontend (cobrem as
  três camadas do Princípio II).
- **Containerização**: Docker + Docker Compose para ambiente local e CI.
- **CI/CD**: GitHub Actions executando lint, type-check, testes (unit/integração/E2E) e
  verificação de cobertura em todo Pull Request.
- **Análise estática de qualidade**: SonarCloud (ou ferramenta equivalente) integrada ao
  pipeline de CI, suportando o gate de qualidade do Princípio I.

Qualquer introdução de nova tecnologia, biblioteca de infraestrutura ou substituição de um item
desta lista DEVE ser registrada como ADR antes da implementação.

## Fluxo de Desenvolvimento e Quality Gates

- Todo Pull Request DEVE passar pelos gates automatizados de CI (lint, type-check, build,
  unit + integração + E2E, cobertura ≥ 80%) antes de poder ser revisado por humanos.
- Todo Pull Request DEVE ser revisado por ao menos uma pessoa além do autor antes do merge,
  verificando aderência aos Princípios I-V desta constituição.
- Toda feature nova que introduza ou altere uma métrica metrológica DEVE referenciar, no plano
  de implementação, a entrada correspondente no catálogo de métricas (Princípio V) — features
  sem essa referência NÃO PODEM avançar da fase de planejamento para a fase de implementação.
- Decisões de arquitetura relevantes (escolha de stack, padrões estruturais, integrações
  externas como a API do GitHub) DEVEM ser registradas como ADR em `docs/adr/`.

## Governance

Esta constituição prevalece sobre qualquer outra prática, convenção ou documento de
desenvolvimento do projeto SoftMeter. Em caso de conflito entre esta constituição e qualquer
outro documento (README, ADR, template de plano), esta constituição prevalece até que seja
formalmente emendada.

**Procedimento de emenda**: Alterações a esta constituição são propostas via comando
`/speckit-constitution`, devem registrar o motivo da alteração e DEVEM atualizar o Sync Impact
Report no topo deste arquivo. Emendas que removam ou redefinam um princípio existente exigem
revisão explícita do impacto sobre `plan-template.md`, `spec-template.md` e `tasks-template.md`.

**Política de versionamento semântico**:
- **MAJOR**: remoção ou redefinição incompatível de um princípio existente.
- **MINOR**: adição de novo princípio ou expansão material de orientação existente.
- **PATCH**: esclarecimentos, correções de redação ou ajustes não semânticos.

**Revisão de conformidade**: Todo Pull Request e todo plano de implementação (`plan.md`) DEVEM
incluir uma verificação explícita de conformidade com os Princípios I-V na seção "Constitution
Check". Violações DEVEM ser justificadas na tabela de "Complexity Tracking" do plano ou
eliminadas antes do merge. Uso de orientação em tempo de execução (CLAUDE.md e demais arquivos
de contexto do agente) DEVE permanecer consistente com esta constituição.

**Version**: 2.0.0 | **Ratified**: 2026-06-24 | **Last Amended**: 2026-06-24
