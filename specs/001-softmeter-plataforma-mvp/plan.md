# Implementation Plan: SoftMeter — Plataforma de Metrologia de Qualidade de Software

**Branch**: `001-softmeter-plataforma-mvp` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-softmeter-plataforma-mvp/spec.md`

## Summary

Construir o MVP do SoftMeter: uma plataforma web onde um usuário autenticado cadastra um
repositório GitHub público (Python ou JavaScript/TypeScript), dispara uma análise sob demanda
que calcula seis métricas (Complexidade Ciclomática, LOC, Índice de Manutenibilidade, Cobertura
de Testes, Acoplamento, Score de Duplicação), visualiza o resultado em um dashboard de gauges
metrológicos com valor medido/limites/status de conformidade, consulta o histórico/tendência de
análises anteriores e gera um relatório técnico em PDF rastreável (definição, fórmula, fonte
bibliográfica e limites por métrica). Abordagem técnica: backend FastAPI (Python 3.12) com
Celery+Redis para análises assíncronas e Radon + parser AST próprio como motor de métricas;
frontend React 18 + TypeScript + Vite com Recharts para os gauges/gráficos; PostgreSQL 16 como
armazenamento; JWT (access+refresh) com bcrypt para autenticação; ReportLab para os PDFs.

## Technical Context

**Language/Version**: Backend: Python 3.12. Frontend: TypeScript 5.x (React 18, via Vite).

**Primary Dependencies**: Backend: FastAPI, SQLAlchemy + Alembic, Celery, Redis (broker/result
backend), Radon, PyJWT (ou python-jose), passlib[bcrypt], ReportLab, httpx (cliente para a API
REST do GitHub). Frontend: React 18, Vite, React Router, Recharts, Axios.

**Storage**: PostgreSQL 16 (dados de domínio: usuários, repositórios, análises, medições,
relatórios). Redis como broker/result backend do Celery (não armazena dados de domínio
permanentes).

**Testing**: Backend: `pytest` + `pytest-cov` (unit + integração, com `httpx`/`TestClient` para
os endpoints FastAPI e um banco PostgreSQL de teste). Frontend: Jest + React Testing Library
(unit + integração de componentes). E2E: Playwright cobrindo os fluxos críticos ponta a ponta
(cadastro de repositório → análise → dashboard) através da UI real, conforme Princípio II.

**Target Platform**: Containers Linux (Docker/Docker Compose) para backend, worker Celery,
PostgreSQL e Redis; navegadores modernos (desktop) para o frontend.

**Project Type**: Web application (frontend + backend separados, conforme Project Structure).

**Performance Goals**: Resultado inicial de uma análise em até 10s (p95) para repositórios de
porte pequeno/médio (Princípio IV); para repositórios maiores, resposta imediata de "análise em
processamento" com conclusão assíncrona via Celery, sem bloquear a UI.

**Constraints**: Cobertura de testes ≥ 80% em backend e frontend (Princípio I); apenas
repositórios GitHub **públicos**; apenas código Python e/ou JavaScript/TypeScript (FR-002);
nenhuma personalização de limites de especificação por usuário nesta versão (FR-013); análise
disparada apenas sob demanda, sem agendamento em segundo plano (FR-012).

**Scale/Scope**: Uso acadêmico individual (TCC) — poucos usuários concorrentes esperados, sem
exigência de escala horizontal; 6 métricas, 5 telas principais (cadastro/lista de repositórios,
dashboard, histórico, relatório, autenticação).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio / Seção | Avaliação | Status |
|---|---|---|
| I. Qualidade de Código (cobertura ≥80%) | `pytest-cov` no backend e Jest no frontend serão configurados no CI com gate de 80%; nenhuma exceção solicitada nesta feature. | PASS |
| II. Testes em Múltiplas Camadas | Unit (services/analysis isolados), Integração (routers FastAPI + repositórios + PostgreSQL de teste, stubs da API do GitHub) e E2E (Playwright) estão todos contemplados na seção Testing acima e nas tasks de cada user story. | PASS |
| III. Consistência de Interface Metrológica | Dashboard usará um único componente de gauge reutilizável (Recharts) para as 6 métricas, com as mesmas faixas de cor do Laudo de Conformidade do projeto — detalhado em data-model.md / contracts. | PASS |
| IV. Performance da Análise (<10s) | Celery+Redis cobre a degradação graciosa para repositórios maiores; teste de performance da análise síncrona será incluído nos critérios de aceite (ver tasks da US1). | PASS |
| V. Rastreabilidade Metrológica (NON-NEGOTIABLE) | Catálogo de métricas (nome, unidade, fórmula, fonte bibliográfica, limites) definido em `data-model.md` *antes* de qualquer endpoint/tela que exiba uma métrica, conforme exigido pelo princípio. | PASS |
| Restrições Tecnológicas e de Stack | Stack do plano (FastAPI/Python 3.12, PostgreSQL 16, Celery/Redis, Radon, React 18/Vite, Recharts, ReportLab, JWT+bcrypt, Docker Compose, GitHub Actions) corresponde exatamente à stack vinculante definida na constituição v2.0.0 (pós-ADR-003). | PASS |
| Fluxo de Desenvolvimento e Quality Gates | PRs desta feature deverão referenciar o catálogo de métricas (Princípio V) e passar pelos gates de CI antes de revisão humana; ADR-003 já registra o pivô de stack exigido antes da implementação. | PASS |

Nenhuma violação identificada; não é necessário preencher a tabela de Complexity Tracking.

**Re-check pós Phase 1 (design)**: `research.md` resolveu todas as incógnitas técnicas (incluindo
a decisão de segurança sobre Cobertura de Testes — sem execução de código de terceiros) e
`data-model.md` definiu o catálogo completo das 6 métricas (nome, unidade, fórmula, fonte
bibliográfica, limites) exigido pelo Princípio V antes de qualquer contrato de API expor uma
métrica (`contracts/analyses.md`, `contracts/reports.md`). Nenhuma violação nova introduzida pelo
design da Phase 1; gates permanecem todos em PASS.

## Project Structure

### Documentation (this feature)

```text
specs/001-softmeter-plataforma-mvp/
├── plan.md              # Este arquivo (/speckit-plan)
├── research.md          # Phase 0 (/speckit-plan)
├── data-model.md         # Phase 1 (/speckit-plan)
├── quickstart.md         # Phase 1 (/speckit-plan)
├── contracts/             # Phase 1 (/speckit-plan)
└── tasks.md              # Phase 2 (/speckit-tasks — não criado por /speckit-plan)
```

### Source Code (repository root)

```text
src/backend/                  # FastAPI (substitui o backend Node/Express do ADR-001, ver ADR-003)
├── app/
│   ├── main.py                # Bootstrap da aplicação FastAPI
│   ├── core/                  # Config, segurança (JWT/bcrypt), Celery app
│   ├── api/                   # Routers: auth, repositories, analyses, reports
│   ├── models/                # Modelos SQLAlchemy (Usuário, Repositório, Análise, Métrica, Medição, Relatório)
│   ├── schemas/                # Schemas Pydantic (request/response)
│   ├── services/                # Regras de negócio (github_service, conformity_service, report_service)
│   ├── analysis/                 # Motor de métricas: adapter Radon + parser AST próprio (acoplamento/duplicação)
│   ├── repositories/              # Acesso a dados (camada de persistência)
│   ├── workers/                    # Tasks Celery (execução assíncrona de análise)
│   └── db/                          # Sessão SQLAlchemy, migrations Alembic
└── tests/
    ├── unit/                        # Regras de negócio e motor de métricas isolados
    └── integration/                  # Routers + repositórios + PostgreSQL de teste

src/frontend/                # React 18 + TypeScript + Vite (já existente, mantido)
├── src/
│   ├── components/            # Inclui o componente de gauge metrológico reutilizável
│   ├── pages/                 # Cadastro/lista de repositórios, Dashboard, Histórico, Relatório, Login/Registro
│   └── services/              # Chamadas à API do backend
└── tests/                     # Testes de componente (Jest + Testing Library)

tests/e2e/                   # Playwright — fluxos ponta a ponta através da UI real
```

**Structure Decision**: Aplicação web com dois projetos (backend + frontend), conforme Option 2
do template. O backend Node/Express criado sob o ADR-001 em `src/backend/` é substituído pelo
serviço FastAPI descrito acima (ADR-003); o frontend React+TypeScript em `src/frontend/` é
mantido, apenas adotando Vite como build tool. Os testes E2E ficam em `tests/e2e/` na raiz do
repositório por cruzarem as duas camadas através da interface real, em vez de pertencerem a um
único projeto.

## Complexity Tracking

> Nenhuma violação da Constitution Check identificada nesta feature — tabela não aplicável.
