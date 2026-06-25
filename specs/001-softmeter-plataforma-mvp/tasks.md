---

description: "Task list for SoftMeter — Plataforma de Metrologia de Qualidade de Software"
---

# Tasks: SoftMeter — Plataforma de Metrologia de Qualidade de Software

**Input**: Design documents from `/specs/001-softmeter-plataforma-mvp/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídas em todas as fases — a Constituição do projeto (Princípio II, NON-NEGOTIABLE)
exige testes unitários, de integração e E2E para toda funcionalidade nova, o que substitui o
padrão "tests opcionais" da geração de tasks.

**Organization**: Tasks agrupadas por user story (spec.md) para permitir implementação e teste
independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tasks incompletas)
- **[Story]**: User story à qual a task pertence (US1–US5); ausente em Setup/Foundational/Polish
- Caminhos de arquivo exatos incluídos em cada descrição

## Path Conventions

- **Backend**: `src/backend/app/`, `src/backend/tests/{unit,integration}/`
- **Frontend**: `src/frontend/src/`, `src/frontend/tests/`
- **E2E**: `tests/e2e/` (na raiz do repositório, cruza as duas camadas — ver `plan.md`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: inicialização do projeto conforme a stack do ADR-003 / `plan.md`

- [X] T001 Criar esqueleto do projeto backend (pyproject.toml/requirements.txt, `src/backend/app/main.py` com bootstrap FastAPI vazio) per Project Structure do `plan.md`
- [X] T002 [P] Criar esqueleto do projeto frontend Vite+React 18+TypeScript em `src/frontend/` (package.json, vite.config.ts), reaproveitando `src/frontend/src/{components,pages,services}` já existentes
- [X] T003 [P] Configurar lint/format do backend (`ruff`, `mypy`) em `src/backend/pyproject.toml`
- [X] T004 [P] Configurar lint/format do frontend (ESLint + Prettier) em `src/frontend/.eslintrc.cjs`
- [X] T005 [P] Escrever `docker-compose.yml` com serviços `postgres` (16), `redis`, `backend`, `celery-worker` e `frontend`
- [X] T006 [P] Criar esqueleto do workflow de CI em `.github/workflows/ci.yml` (jobs de lint, type-check e teste para backend e frontend)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: infraestrutura central que bloqueia todas as user stories — inclui autenticação
(FR-010 exige usuário autenticado em toda rota das demais stories) e o catálogo de métricas
(Princípio V exige a entrada do catálogo antes de qualquer exibição/cálculo de métrica)

**⚠️ CRITICAL**: nenhuma user story pode iniciar antes desta fase estar completa

- [X] T007 Configurar engine/sessão SQLAlchemy e framework de migrations Alembic em `src/backend/app/db/`
- [X] T008 [P] Criar modelo SQLAlchemy de Usuário em `src/backend/app/models/user.py`
- [X] T009 [P] Definir o catálogo fixo das 6 métricas (nome, unidade, fórmula, fonte bibliográfica, limites — ver `data-model.md`) em `src/backend/app/analysis/metrics_catalog.py`
- [X] T010 Implementar utilitários de hashing de senha (bcrypt) em `src/backend/app/core/security.py`
- [X] T011 Implementar emissão/validação de JWT (access + refresh token) em `src/backend/app/core/security.py` (depende de T010)
- [X] T012 Implementar dependency `get_current_user` (FastAPI `Depends`) em `src/backend/app/core/dependencies.py` (depende de T011)
- [X] T013 [P] Configurar app Celery + broker/result backend Redis em `src/backend/app/core/celery_app.py`
- [X] T014 Implementar endpoint `POST /api/v1/auth/register` em `src/backend/app/api/auth.py` (depende de T008, T010, T011)
- [X] T015 Implementar endpoint `POST /api/v1/auth/login` em `src/backend/app/api/auth.py` (depende de T014)
- [X] T016 Implementar endpoints `POST /api/v1/auth/refresh` e `POST /api/v1/auth/logout` em `src/backend/app/api/auth.py` (depende de T015)
- [X] T017 Conectar routers, CORS e exception handlers no bootstrap em `src/backend/app/main.py` (depende de T014–T016)
- [X] T018 [P] Configurar roteamento (React Router) e layout base em `src/frontend/src/App.tsx`
- [X] T019 [P] Implementar cliente de API (Axios com header de auth + refresh interceptor) em `src/frontend/src/services/apiClient.ts` (reaproveitado o `services/api.ts` já existente em vez de duplicar o arquivo)
- [X] T020 [P] Implementar componente `ProtectedRoute` (redireciona para login se não autenticado) em `src/frontend/src/components/ProtectedRoute.tsx`
- [X] T021 [P] Testes unitários dos utilitários de segurança (hash, JWT) em `src/backend/tests/unit/test_security.py`
- [X] T022 Testes de integração dos endpoints de autenticação em `src/backend/tests/integration/test_auth_api.py` (depende de T014–T016)

**Checkpoint**: fundação pronta — implementação das user stories pode começar

---

## Phase 3: User Story 1 - Cadastro de repositório e execução de análise automática (Priority: P1) 🎯 MVP

**Goal**: usuário cadastra um repositório GitHub público (Python/JS/TS) e dispara uma análise que
calcula e persiste as 6 métricas.

**Independent Test**: cadastrar a URL de um repositório público, disparar análise, confirmar que
um registro de Análise com 6 Medições é armazenado.

### Tests for User Story 1 ⚠️

> Escrever estes testes primeiro; devem falhar antes da implementação

- [ ] T023 [P] [US1] Teste unitário do `GithubService` (linguagens via API, download/extração de zipball, HTTP mockado) em `src/backend/tests/unit/test_github_service.py`
- [ ] T024 [P] [US1] Teste unitário do motor de métricas Radon (Python) + tree-sitter (JS/TS) para Complexidade Ciclomática/LOC/MI em `src/backend/tests/unit/test_metric_engine.py`
- [ ] T025 [P] [US1] Teste unitário dos calculadores de Acoplamento e Score de Duplicação em `src/backend/tests/unit/test_coupling_duplication.py`
- [ ] T026 [P] [US1] Teste unitário do leitor de artefatos de Cobertura de Testes (coverage.xml/lcov.info/badge, e caso "Não disponível") em `src/backend/tests/unit/test_coverage_reader.py`
- [ ] T027 [P] [US1] Teste unitário do classificador de conformidade (valor × limites do catálogo) em `src/backend/tests/unit/test_conformity.py`
- [ ] T028 [US1] Teste de integração dos endpoints de Repositórios, incluindo rejeição por linguagem (FR-002), duplicidade (FR-015) e repositório inacessível (FR-014) em `src/backend/tests/integration/test_repositories_api.py`
- [ ] T029 [US1] Teste de integração dos endpoints de Análise (caminho síncrono e assíncrono 202, falha) em `src/backend/tests/integration/test_analyses_api.py`
- [ ] T030 [US1] Teste E2E: cadastro de repositório + execução de análise pela UI real em `tests/e2e/cadastro_analise.spec.ts`

### Implementation for User Story 1

- [ ] T031 [P] [US1] Criar modelo SQLAlchemy de Repositório em `src/backend/app/models/repository.py`
- [ ] T032 [P] [US1] Criar modelos SQLAlchemy de Análise e Medição em `src/backend/app/models/analysis.py`
- [ ] T033 [US1] Implementar `GithubService` (consulta `languages`, download e extração de zipball — ver `research.md` itens 1–2) em `src/backend/app/services/github_service.py` (depende de T031)
- [ ] T034 [US1] Implementar adapter Radon (Python) e adapter tree-sitter (JS/TS) para Complexidade Ciclomática/LOC/MI em `src/backend/app/analysis/metric_engine.py` (depende de T009)
- [ ] T035 [US1] Implementar calculador de Acoplamento (Instabilidade de Módulo) em `src/backend/app/analysis/coupling.py` (depende de T009)
- [ ] T036 [US1] Implementar calculador de Score de Duplicação (shingling de tokens normalizados) em `src/backend/app/analysis/duplication.py` (depende de T009)
- [ ] T037 [US1] Implementar leitor de artefatos de Cobertura de Testes em `src/backend/app/analysis/coverage_reader.py` (depende de T009)
- [ ] T038 [US1] Implementar `ConformityService` (compara valor medido aos limites do catálogo e define status) em `src/backend/app/services/conformity_service.py` (depende de T034–T037)
- [ ] T039 [US1] Implementar Celery task `run_analysis` (orquestra download, 6 métricas, persistência, e dispara caminho síncrono/assíncrono — ver `research.md` item 7) em `src/backend/app/workers/analysis_tasks.py` (depende de T033, T038)
- [ ] T040 [US1] Implementar endpoints de Repositório (`POST`/`GET`/`GET {id}`/`DELETE`) em `src/backend/app/api/repositories.py` (depende de T033)
- [ ] T041 [US1] Implementar endpoints de Análise (`POST` disparo, `GET {id}` status/resultado) em `src/backend/app/api/analyses.py` (depende de T039)
- [ ] T042 [P] [US1] Implementar página de cadastro/lista de repositórios em `src/frontend/src/pages/RepositoriesPage.tsx`
- [ ] T043 [US1] Implementar serviço de disparo de análise + polling de status em `src/frontend/src/services/analysisService.ts` (depende de T042)

**Checkpoint**: User Story 1 completa e testável de forma independente (via API ou UI)

---

## Phase 4: User Story 2 - Visualização de métricas em dashboard estilo gauge metrológico (Priority: P1) 🎯 MVP

**Goal**: usuário visualiza a análise mais recente como 6 gauges metrológicos (valor, limites,
status de conformidade).

**Independent Test**: com 1 análise concluída, abrir o dashboard e ver os 6 gauges corretos.

### Tests for User Story 2 ⚠️

- [ ] T044 [P] [US2] Teste unitário do componente `Gauge` (faixas de cor por status de conformidade) em `src/frontend/tests/Gauge.test.tsx`
- [ ] T045 [US2] Teste de integração da `DashboardPage` (renderiza 6 gauges a partir de uma análise mock) em `src/frontend/tests/DashboardPage.test.tsx`
- [ ] T046 [US2] Teste E2E: abrir dashboard após análise concluída e verificar os 6 gauges em `tests/e2e/dashboard_gauges.spec.ts`

### Implementation for User Story 2

- [ ] T047 [P] [US2] Implementar componente reutilizável `Gauge` (Recharts; zonas verde/amarelo/vermelho conforme Princípio III) em `src/frontend/src/components/Gauge.tsx`
- [ ] T048 [US2] Implementar `DashboardPage` consumindo `GET /repositories/{id}/analyses/{analysis_id}` e renderizando os 6 `Gauge` em `src/frontend/src/pages/DashboardPage.tsx` (depende de T047)

**Checkpoint**: User Stories 1 e 2 (MVP completo) funcionais

---

## Phase 5: User Story 3 - Histórico de análises e identificação de tendências (Priority: P2)

**Goal**: usuário consulta o histórico cronológico de análises e a tendência de cada métrica.

**Independent Test**: com 2+ análises do mesmo repositório, a tela de histórico mostra a lista
cronológica e a tendência (melhorando/piorando/estável) de uma métrica escolhida.

### Tests for User Story 3 ⚠️

- [ ] T049 [P] [US3] Teste unitário do cálculo de tendência (compara as duas análises mais recentes) em `src/backend/tests/unit/test_trend_service.py`
- [ ] T050 [US3] Teste de integração do endpoint de histórico `GET /repositories/{id}/analyses` (incl. `?metrica=`) em `src/backend/tests/integration/test_analyses_history_api.py`
- [ ] T051 [US3] Teste E2E: histórico com múltiplas análises exibindo tendência em `tests/e2e/historico_tendencia.spec.ts`

### Implementation for User Story 3

- [ ] T052 [P] [US3] Implementar `TrendService` (melhorando/piorando/estável por métrica) em `src/backend/app/services/trend_service.py`
- [ ] T053 [US3] Implementar endpoint de histórico `GET /repositories/{id}/analyses` em `src/backend/app/api/analyses.py` (depende de T052)
- [ ] T054 [P] [US3] Implementar `HistoryPage` com lista cronológica de análises em `src/frontend/src/pages/HistoryPage.tsx`
- [ ] T055 [US3] Implementar componente `TrendChart` (Recharts, série temporal por métrica) em `src/frontend/src/components/TrendChart.tsx` (depende de T054)

**Checkpoint**: User Stories 1–3 funcionais

---

## Phase 6: User Story 4 - Geração de relatório técnico em PDF (Priority: P2)

**Goal**: usuário gera um relatório PDF rastreável (valor, fórmula, fonte, limites por métrica).

**Independent Test**: a partir de uma análise concluída, gerar o PDF e confirmar que todas as 6
métricas exibem definição completa.

### Tests for User Story 4 ⚠️

- [ ] T056 [P] [US4] Teste unitário do `ReportBuilderService` (conteúdo inclui fórmula/fonte/limites de cada métrica) em `src/backend/tests/unit/test_report_builder.py`
- [ ] T057 [US4] Teste de integração dos endpoints de Relatório (`analise_unica`, `historico_completo`, 422 sem análise concluída) em `src/backend/tests/integration/test_reports_api.py`
- [ ] T058 [US4] Teste E2E: gerar e baixar relatório PDF a partir do dashboard em `tests/e2e/relatorio_pdf.spec.ts`

### Implementation for User Story 4

- [ ] T059 [P] [US4] Criar modelo SQLAlchemy de Relatório em `src/backend/app/models/report.py`
- [ ] T060 [US4] Implementar `ReportBuilderService` (ReportLab, usando o catálogo de métricas — ver `research.md` item 8) em `src/backend/app/services/report_service.py` (depende de T009, T059)
- [ ] T061 [US4] Implementar endpoints `POST .../reports` e `GET .../reports/{id}/download` em `src/backend/app/api/reports.py` (depende de T060)
- [ ] T062 [US4] Adicionar botão "Gerar relatório" e link de download no dashboard em `src/frontend/src/pages/DashboardPage.tsx` (depende de T048, T061)

**Checkpoint**: User Stories 1–4 funcionais

---

## Phase 7: User Story 5 - Autenticação de usuários (Priority: P3)

**Goal**: visitante cria conta, faz login e só acessa seus próprios dados.

**Nota de dependência**: os primitivos de backend de autenticação (modelo de Usuário, hashing,
JWT, endpoints `/auth/*`) já foram implementados na Phase 2 (Foundational), pois FR-010 exige
autenticação em toda rota usada pelas demais user stories. Esta fase cobre as telas e o
comportamento de redirecionamento exigidos pelos critérios de aceite da US5.

**Independent Test**: um novo visitante se cadastra, faz login, e só vê os repositórios que ele
próprio cadastrou.

### Tests for User Story 5 ⚠️

- [ ] T063 [P] [US5] Teste de integração garantindo isolamento de dados entre contas (FR-011, SC-006) em `src/backend/tests/integration/test_data_isolation.py`
- [ ] T064 [US5] Teste E2E: cadastro, login e redirecionamento ao acessar rota protegida sem autenticação em `tests/e2e/autenticacao.spec.ts`

### Implementation for User Story 5

- [ ] T065 [P] [US5] Implementar `LoginPage` em `src/frontend/src/pages/LoginPage.tsx`
- [ ] T066 [P] [US5] Implementar `RegisterPage` em `src/frontend/src/pages/RegisterPage.tsx`
- [ ] T067 [US5] Integrar `ProtectedRoute` com redirecionamento para login nas rotas de repositórios/dashboard/histórico/relatório em `src/frontend/src/App.tsx` (depende de T020, T065, T066)

**Checkpoint**: todas as user stories (US1–US5) funcionais

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: qualidade transversal exigida pela constituição (Princípios I e IV)

- [ ] T068 [P] Configurar gate de cobertura ≥80% no CI (`pytest-cov` no backend, Jest no frontend) em `.github/workflows/ci.yml`
- [ ] T069 [P] Teste de performance validando análise síncrona em até 10s p95 (Princípio IV) em `src/backend/tests/integration/test_analysis_performance.py`
- [ ] T070 [P] Endurecimento de segurança: validação de input (formato de URL, tamanho de payload) e rate limiting básico em `src/backend/app/main.py`
- [ ] T071 [P] Atualizar `README.md` e `specs/001-softmeter-plataforma-mvp/quickstart.md` com instruções finais da stack FastAPI
- [ ] T072 Executar a validação manual completa descrita em `quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode iniciar imediatamente
- **Foundational (Phase 2)**: depende do Setup — bloqueia todas as user stories (inclui auth e catálogo de métricas)
- **User Stories (Phase 3–7)**: todas dependem da Foundational
  - US1 (P1) e US2 (P1) formam o MVP demonstrável (análise + dashboard)
  - US3 e US4 (P2) dependem de já existirem análises concluídas (produzidas pela US1)
  - US5 (P3) depende apenas da Foundational para o backend; a fase 7 adiciona somente as telas
- **Polish (Phase 8)**: depende de todas as user stories desejadas estarem completas

### User Story Dependencies

- **US1 (P1)**: depende apenas da Foundational
- **US2 (P1)**: depende da Foundational e dos dados produzidos pela US1 (uma análise concluída) para ser demonstrada, mas seu código (componente `Gauge`, `DashboardPage`) pode ser desenvolvido em paralelo com a US1 usando dados mockados
- **US3 (P2)**: depende de US1 (precisa de análises históricas) e do componente de gráfico ser compatível com a UI da US2
- **US4 (P2)**: depende de US1 (precisa de uma análise concluída) e do catálogo de métricas (Foundational)
- **US5 (P3)**: backend já coberto na Foundational; a UI desta fase pode ser construída em paralelo com US1–US4

### Within Each User Story

- Testes (unit + integração) são escritos antes da implementação e devem falhar primeiro
- Modelos antes de serviços; serviços antes de endpoints; endpoints antes da integração de frontend
- Teste E2E da story só passa após toda a cadeia backend+frontend da story estar implementada

### Parallel Opportunities

- Todas as tasks `[P]` de uma mesma fase podem rodar em paralelo entre si
- Todos os testes `[P]` de uma user story podem ser escritos em paralelo antes da implementação
- US2, US3, US4 e US5 podem ser desenvolvidas em paralelo por pessoas diferentes depois que US1 expõe os endpoints de Análise (contrato estável), desde que usem dados mockados onde a dependência ainda não estiver pronta

---

## Parallel Example: User Story 1

```bash
# Testes da User Story 1 em paralelo:
Task: "Teste unitário do GithubService em src/backend/tests/unit/test_github_service.py"
Task: "Teste unitário do motor de métricas em src/backend/tests/unit/test_metric_engine.py"
Task: "Teste unitário de acoplamento/duplicação em src/backend/tests/unit/test_coupling_duplication.py"
Task: "Teste unitário do leitor de cobertura em src/backend/tests/unit/test_coverage_reader.py"
Task: "Teste unitário do classificador de conformidade em src/backend/tests/unit/test_conformity.py"

# Modelos da User Story 1 em paralelo:
Task: "Criar modelo Repositório em src/backend/app/models/repository.py"
Task: "Criar modelos Análise e Medição em src/backend/app/models/analysis.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (CRÍTICO — bloqueia todas as stories)
3. Completar Phase 3: User Story 1 (cadastro + análise)
4. Completar Phase 4: User Story 2 (dashboard de gauges)
5. **PARAR e VALIDAR**: testar US1+US2 de forma independente (cadastrar repo real, ver gauges)
6. Demo/deploy do MVP

> Embora o teste de independência da US1 (definido em `spec.md`) seja satisfeito apenas com a
> API, o valor demonstrável do MVP do TCC exige visualizar o resultado — por isso o MVP sugerido
> aqui é US1+US2 (ambas P1), não apenas US1.

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 + US2 → MVP demonstrável (Demo/Deploy)
3. US3 → adiciona histórico/tendências (Demo/Deploy)
4. US4 → adiciona relatório PDF (Demo/Deploy)
5. US5 → adiciona telas de autenticação completas (Demo/Deploy)
6. Polish → qualidade transversal (cobertura, performance, segurança)

---

## Notes

- `[P]` = arquivos diferentes, sem dependências entre si
- `[Story]` mapeia a task à user story correspondente para rastreabilidade
- Verificar que os testes falham antes de implementar
- Fazer commit após cada task ou grupo lógico de tasks
- Parar em qualquer checkpoint para validar a story isoladamente
- O catálogo de métricas (T009) é o gate do Princípio V: nenhuma task de implementação de
  métrica (T034–T037) ou de exibição (T047, T060) pode ser concluída sem T009 já estar pronta
