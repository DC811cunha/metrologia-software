<!--
Sync Impact Report
==================
Version change: TEMPLATE → 1.0.0 (initial ratification)
Rationale: First concrete constitution for SoftMeter, filling all template placeholders.
This is a MAJOR version because it establishes the baseline governing principles
(no prior ratified version existed to compare against).

Modified principles: N/A (initial ratification, no renames)

Principles added:
- I. Qualidade de Código com Cobertura Mínima de 80%
- II. Disciplina de Testes em Múltiplas Camadas (Unit, Integração e E2E)
- III. Consistência de Interface Metrológica
- IV. Performance da Análise (< 10 segundos)
- V. Rastreabilidade Metrológica das Métricas (NON-NEGOTIABLE)

Sections added:
- Restrições Tecnológicas e de Stack
- Fluxo de Desenvolvimento e Quality Gates
- Governance

Sections removed: none (template placeholders replaced, no prior content existed)

Templates requiring updates:
- ✅ .specify/templates/plan-template.md — generic "[Gates determined based on constitution
  file]" placeholder already defers to this document; no edit needed, gate content will be
  filled per-feature by /speckit-plan referencing principles I-V.
- ✅ .specify/templates/spec-template.md — generic, technology-agnostic; no changes required.
- ✅ .specify/templates/tasks-template.md — generic task categorization already accommodates
  unit/integration/E2E test phases and polish/performance tasks required by Principles II and IV.
- ⚠ No command files found under .specify/templates/commands/ (directory does not exist in
  this installation) — nothing to update.
- ⚠ README.md documents the metrology classification thresholds (≥90% Conforme, 70-89%
  Condicional, <70% Não-Conforme) referenced by Principle III; kept consistent, no edit needed.

Follow-up TODOs:
- TODO(METRICS_CATALOG_LOCATION): exact path for the metrics catalog required by Principle V
  (e.g., docs/metrics/) should be formalized in the next plan that introduces metric definitions.
-->

# SoftMeter Constitution

## Core Principles

### I. Qualidade de Código com Cobertura Mínima de 80%

Todo código de produção (backend `src/backend/src/` e frontend `src/frontend/src/`) DEVE manter
cobertura automatizada de testes igual ou superior a 80%, medida em linhas e branches pelos
relatórios de cobertura do Jest. Pipelines de CI DEVEM bloquear merge de Pull Requests que
reduzam a cobertura abaixo do limiar vigente ou que introduzam regressão de cobertura em
arquivos já cobertos. Lint e checagem de tipos (TypeScript `strict`) DEVEM passar sem erros
antes de qualquer merge; alertas de análise estática (SonarCloud ou equivalente) classificados
como bloqueantes DEVEM ser resolvidos antes do merge.

**Rationale**: Assim como uma peça fora de tolerância dimensional é refugada na indústria,
código sem cobertura mínima comprovada não pode ser aceito como "conforme". O limiar de 80%
é o critério objetivo e verificável que substitui a afirmação subjetiva de que o software
"está pronto".

### II. Disciplina de Testes em Múltiplas Camadas (Unit, Integração e E2E)

Toda funcionalidade nova ou alterada DEVE ser validada nas três camadas de teste do projeto:

- **Testes unitários**: cobrem regras de negócio isoladas em `services/`, sem I/O real
  (banco de dados, rede, sistema de arquivos mockados).
- **Testes de integração**: validam contratos entre camadas reais — `controllers/` +
  `routes/` + `repositories/` contra um banco de dados de teste, e chamadas reais à API do
  GitHub via fixtures/stubs controlados.
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

A stack tecnológica documentada no README do projeto é vinculante para todo desenvolvimento,
salvo decisão registrada em ADR (`docs/adr/`):

- **Backend**: Node.js + TypeScript + Express, em `src/backend/`.
- **Frontend**: React + TypeScript (SPA), em `src/frontend/`.
- **Banco de dados**: PostgreSQL.
- **Testes**: Jest + Testing Library (cobre as três camadas do Princípio II).
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

**Version**: 1.0.0 | **Ratified**: 2026-06-24 | **Last Amended**: 2026-06-24
