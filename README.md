# SoftMeter 📐

> **Metrologia de Software** — Plataforma de Inspeção e Conformidade de Qualidade de Software

[![CI](https://github.com/SEU_USUARIO/metrologia-software/actions/workflows/ci.yml/badge.svg)](https://github.com/SEU_USUARIO/metrologia-software/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🎯 O Problema

Softwares são entregues como "prontos" sem que existam critérios objetivos e quantitativos
que comprovem essa afirmação. Na indústria manufatureira, nenhuma peça é aceita sem
medição — existem tolerâncias, laudos de inspeção e protocolos de conformidade.

**Por que o software não tem o mesmo rigor?**

O SoftMeter traz o protocolo da metrologia industrial para a Engenharia de Software:
cada requisito recebe um **valor nominal** e **tolerâncias** (assim como uma cota dimensional),
cada ciclo de testes gera **medições com desvios calculados automaticamente** e cada entrega
resulta em um **Laudo de Conformidade de Software** — Conforme, Condicional ou Não-Conforme.

---

## 🗂️ Estrutura do Repositório

```
metrologia-software/
├── specs/
│   └── 001-softmeter-plataforma-mvp/   # Spec, ADRs, data model, tasks
├── src/
│   ├── backend/                    # API FastAPI + Python 3.12
│   │   ├── app/
│   │   │   ├── api/                # Routers: auth, repositories, analyses, reports
│   │   │   ├── analysis/           # Motores de métricas (CC, LOC, MI, acoplamento, duplicação)
│   │   │   ├── core/               # Config, segurança JWT, dependências
│   │   │   ├── models/             # SQLAlchemy ORM models
│   │   │   ├── schemas/            # Pydantic request/response schemas
│   │   │   ├── services/           # GitHub, análise, relatório, conformidade, tendência
│   │   │   └── workers/            # Celery tasks (análise assíncrona)
│   │   ├── alembic/                # Migrations do banco de dados
│   │   ├── tests/
│   │   │   ├── unit/               # Testes unitários (métricas, conformidade, PDF)
│   │   │   └── integration/        # Testes de integração (APIs, isolamento, performance)
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   └── frontend/                   # SPA React 18 + TypeScript + Vite + Tailwind CSS
│       ├── src/
│       │   ├── components/         # Gauge, TrendChart, AppLayout, UI atoms
│       │   ├── pages/              # Login, Register, Repositories, Dashboard, History
│       │   └── services/           # Clientes axios: analysis, report, repository
│       ├── tests/                  # Testes de componentes (Jest + Testing Library)
│       ├── package.json
│       └── Dockerfile
├── .github/
│   └── workflows/
│       └── ci.yml                  # CI: lint + mypy + pytest (≥80%) + ESLint + Jest (≥80%)
├── docker-compose.yml              # PostgreSQL + Redis + backend + worker Celery + frontend
└── README.md
```

---

## 🚀 Como rodar localmente

### Pré-requisitos

- [Docker Desktop](https://www.docker.com/) (inclui Docker Compose v2)
- [Git](https://git-scm.com/)

### Setup em 3 passos

```bash
# 1. Clone o repositório
git clone https://github.com/SEU_USUARIO/metrologia-software.git
cd metrologia-software

# 2. Suba o ambiente completo (PostgreSQL, Redis, backend FastAPI, Celery worker, frontend)
docker compose up --build -d

# 3. Aplique as migrations do banco de dados
docker compose exec backend alembic upgrade head
```

A aplicação estará disponível em:

- **Frontend:** <http://localhost:3000>
- **Backend API (Swagger):** <http://localhost:3001/docs>
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

### Rodando os testes

```bash
# Backend (Python 3.12, requer venv local)
cd src/backend
pip install -e ".[dev]"
pytest --cov=app --cov-report=term-missing

# Frontend
cd src/frontend
npm install
npm test

# E2E (Playwright) — requer a aplicação completa rodando (ver tests/e2e/README.md)
cd tests/e2e
npm install
npx playwright install --with-deps chromium
npm test
```

Ver também o [Quickstart completo de validação manual](specs/001-softmeter-plataforma-mvp/quickstart.md).

---

## 🏗️ Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.0 | Tipagem nativa, ecossistema científico (Radon, tree-sitter) |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS | Componentização, design system consistente |
| Banco de dados | PostgreSQL 16 | Robusto, relacional, suportado nas diretrizes do portfólio |
| Fila de tarefas | Celery + Redis | Análise assíncrona de repositórios grandes |
| Motor de métricas | Radon (CC/LOC/MI) + tree-sitter (JS/TS) | Bibliotecas especializadas por linguagem |
| Relatórios | ReportLab + Bitstream Vera TTF | PDF gerado server-side com Unicode |
| Testes | pytest + Jest + Testing Library | TDD full-stack, cobertura ≥80% em CI |
| Container | Docker + Docker Compose | Ambiente local idêntico à produção |
| CI/CD | GitHub Actions | Lint + mypy + pytest + ESLint + Jest a cada push |

---

## 📐 O Framework Metrológico

### Analogia Metrologia Industrial × Software

| Metrologia Industrial | SoftMeter |
|---|---|
| Desenho técnico / GD&T | Documento de Requisitos |
| Tolerância dimensional | Tolerância por requisito (sup/inf) |
| Medição com Braço FARO | Coleta de valores em ciclo de testes |
| Software PolyWorks | SoftMeter |
| Laudo de Inspeção | Laudo de Conformidade de Software |
| Peça aprovada / refugada | Software Conforme / Não-Conforme |

### Classificação do Laudo

| Índice de Conformidade | Classificação |
|---|---|
| ≥ 90% | ✅ Conforme |
| 70% – 89% | ⚠️ Condicional |
| < 70% | ❌ Não-Conforme |

> **Obs.:** Qualquer requisito com criticidade **Crítica** reprovado resulta em Não-Conforme independente do índice geral.

---

## 📋 Documentação

- 📄 [RFC-001 — Documento de Proposta do Projeto](docs/rfc/RFC-001-metrologia-software.md)
- 🏛️ [Decisões de Arquitetura (ADR)](docs/adr/)
- 🖼️ [Diagramas C4](docs/architecture/)

---

## 📚 Referências Acadêmicas

- BASILI, V.R. et al. **Goal Question Metric Paradigm** (1994)
- VIM — **Vocabulário Internacional de Metrologia**, INMETRO (2012)
- ISO/IEC 25010:2023 — **SQuaRE — Product Quality Model**
- SOMMERVILLE, Ian. **Engenharia de Software**, 9ª ed. (2011)
- WINCK, D.V. **Mais Que Código**, Medium (2026)

---

## 🎓 Contexto Acadêmico

Este projeto é o Trabalho de Conclusão de Curso (Portfólio) do curso de **Engenharia de Software**
da **Católica SC**, desenvolvido segundo as diretrizes do [Portfolio Playbook](https://github.com/CatolicaSC-Portfolio/The-Portfolio-Playbook).

**Disciplinas envolvidas:**
- PAC Extensionista VII (RFC e planejamento)
- PAC Extensionista VIII (validação e QA por pares)
- Portfólio (desenvolvimento e entrega — Poster + Demo Day)

---

## 📝 Licença

Este projeto está licenciado sob a [MIT License](LICENSE).
