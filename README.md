# SoftMeter 📐

> **Metrologia de Software** — Plataforma de Inspeção e Conformidade de Qualidade de Software

[![CI](https://github.com/DC811cunha/metrologia-software/actions/workflows/ci.yml/badge.svg)](https://github.com/DC811cunha/metrologia-software/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🎯 O Problema

Softwares são entregues como "prontos" sem que existam critérios objetivos e quantitativos
que comprovem essa afirmação. Na indústria manufatureira, nenhuma peça é aceita sem
medição — existem tolerâncias, laudos de inspeção e protocolos de conformidade.

**Por que o software não tem o mesmo rigor?**

O SoftMeter traz o protocolo da metrologia industrial para a Engenharia de Software:
analisa **automaticamente** o código-fonte de repositórios GitHub públicos (Python, JavaScript e
TypeScript) e calcula **6 métricas objetivas** — Complexidade Ciclomática, LOC, Índice de
Manutenibilidade, Cobertura de Testes, Acoplamento e Score de Duplicação. Cada métrica tem
fórmula, unidade, fonte bibliográfica e **limites de especificação** (como uma cota com
tolerância), e nenhum valor é digitado à mão. O resultado aparece em um dashboard de gauges, com
histórico e tendência, e vira um **Laudo de Conformidade de Software** em PDF — Conforme,
Condicional ou Não-Conforme.

---

## 🗂️ Estrutura do Repositório

```
metrologia-software/
├── specs/
│   └── 001-softmeter-plataforma-mvp/   # Spec, plano, pesquisa, data model, contratos, tasks
├── src/
│   ├── backend/                    # API FastAPI + Python 3.12
│   │   ├── app/
│   │   │   ├── api/                # Routers: auth, repositories, analyses, reports
│   │   │   ├── analysis/           # Motores de métricas (CC, LOC, MI, acoplamento, duplicação)
│   │   │   ├── core/               # Config, segurança JWT, rate limit, dependências
│   │   │   ├── models/             # SQLAlchemy ORM models
│   │   │   ├── schemas/            # Pydantic request/response schemas
│   │   │   ├── services/           # GitHub, análise, relatório, conformidade, tendência, sincronia do cadastro
│   │   │   └── workers/            # Celery tasks (análise assíncrona, e-mail de recuperação)
│   │   ├── alembic/                # Migrations do banco de dados
│   │   ├── tests/
│   │   │   ├── unit/               # Testes unitários (métricas, conformidade, PDF, e-mail, segurança)
│   │   │   └── integration/        # Testes de integração (APIs, isolamento, performance)
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   └── frontend/                   # SPA React 18 + TypeScript + Vite + Tailwind CSS
│       ├── src/
│       │   ├── components/         # Gauge, TrendChart, AppLayout/AuthLayout, home/ (landing + tutorial), ui/ (Button, Card, ...)
│       │   ├── pages/              # Home, Login, Register, ForgotPassword, ResetPassword,
│       │   │                       # Repositories, Dashboard, History
│       │   └── services/           # Clientes axios: analysis, report, repository
│       ├── tests/                  # Testes de componentes (Jest + Testing Library)
│       ├── package.json
│       └── Dockerfile
├── tests/
│   └── e2e/                        # Playwright — fluxos ponta a ponta pela UI real
├── docs/
│   ├── rfc/                        # RFC-001 (v2.2): proposta, requisitos, arquitetura, segurança
│   ├── adr/                        # Decisões de arquitetura (ADR-001 a ADR-015)
│   ├── architecture/               # Diagramas C4 e fluxos de dados
│   ├── deploy/                     # Roteiro de deploy público na AWS
│   ├── archive/                    # Backend Node/Express original (descontinuado, ADR-003)
│   └── outros/                     # Relatório do PAC (docx/pdf)
├── .github/
│   ├── dependabot.yml              # Atualizações semanais de dependências (pip, npm, Actions, Docker)
│   └── workflows/
│       ├── audit.yml               # pip-audit + npm audit (semanal e ao mudar dependências)
│       └── ci.yml                  # CI: ruff + mypy + pytest (≥80%) + ESLint + tsc + Jest (≥80%)
├── docker-compose.yml              # Desenvolvimento: PostgreSQL + Redis + backend + worker Celery + frontend
├── docker-compose.prod.yml         # Produção: sem portas de banco/Redis, credenciais obrigatórias (ADR-007)
├── .env.example                    # Modelo das variáveis de ambiente (copie para .env)
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
git clone https://github.com/DC811cunha/metrologia-software.git
cd metrologia-software

# 2. Suba o ambiente completo (PostgreSQL, Redis, backend FastAPI, Celery worker, frontend)
docker compose up --build -d

# 3. Aplique as migrations do banco de dados
docker compose exec backend alembic upgrade head
```

O `.env` é opcional — sem ele, valem os padrões de desenvolvimento do `docker-compose.yml`. Para
habilitar recursos que dependem de serviços externos, copie [`.env.example`](.env.example) para
`.env` e preencha:

- `GITHUB_TOKEN` — permite ler a cobertura de testes publicada como artifact do GitHub Actions do
  repositório analisado e sobe o limite da API de 60 para 5000 req/h (ADR-004). Um token
  expirado não quebra o sistema: ele segue sem credenciais.
- `RESEND_API_KEY` — envia o e-mail de recuperação de senha; sem ela, o link de redefinição é
  registrado no log do worker Celery (`docker compose logs celery-worker`) (ADR-005).

A aplicação estará disponível em:

- **Frontend:** <http://localhost:3000>
- **Backend API (Swagger):** <http://localhost:3001/docs>
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

### Rodando os testes

```bash
# Backend (Python 3.12, requer venv local)
cd src/backend
pip install -c requirements.txt -e ".[dev]"   # versões fixas, as mesmas do Docker e do CI
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

### Desenvolvimento × produção

O `docker-compose.yml` é **somente para desenvolvimento**: publica o Postgres (`5432`) e o Redis (`6379`,
sem senha) em todas as interfaces, usa senhas e segredos JWT padrão e roda o backend com `--reload` e o
código montado como volume. **Não o use para publicar a aplicação.**

Para produção há o `docker-compose.prod.yml`: sem portas de banco/Redis, sem `--reload`, Redis com senha
e todas as credenciais obrigatórias (o `compose` recusa subir se alguma faltar). Ele cobre backend, worker,
Postgres e Redis; o frontend deve ser servido como build estático (`npm run build`) por um proxy reverso
com HTTPS, que também encaminha `/api` ao backend.

```bash
# 1. Defina as variáveis (ver comentários no .env.example): DB_PASSWORD, REDIS_PASSWORD, JWT_SECRET,
#    JWT_REFRESH_SECRET, FRONTEND_URL, CORS_ORIGINS, FORWARDED_ALLOW_IPS
# 2. Suba e aplique as migrations
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
```

O backend de produção usa o estágio `prod` do `Dockerfile` (sem extras de teste, sem `--reload`, rodando como
usuário comum) e os PDFs dos relatórios ficam em um **volume nomeado** (`reports_data_prod`): sem ele, cada
recriação do container apagaria todos os relatórios já emitidos.

Com `ENVIRONMENT=production` a API **se recusa a iniciar** com segredos JWT padrão ou curtos (< 32
caracteres), `JWT_SECRET` igual a `JWT_REFRESH_SECRET`, `COOKIE_SECURE` desligado ou a senha padrão do banco.

### Segurança e limites

Resumo do que a API faz para ser exposta publicamente (detalhes nos ADRs):

- **Sessão (ADR-006):** access token de 15 min; refresh token de 7 dias **somente** em cookie `HttpOnly`.
  O logout e o reset de senha revogam os tokens no servidor (`token_version`), em todos os dispositivos.
  Senhas de 8 a 72 bytes (limite do bcrypt).
- **Rate limit por IP (ADR-008):** login, recuperação e redefinição de senha: 10/min. Em produção, também
  cadastro (10/h), refresh (30/min) e criação de análises (20/h). `RATE_LIMIT_BACKEND=redis` compartilha o
  contador entre réplicas. Corpo das requisições limitado a 64 KB.
- **Custo da análise (ADR-009):** repositórios acima de 200 MB são recusados; download (100 MB),
  conteúdo extraído (400 MB), número de arquivos (30 000) e tempo (300 s) têm teto. Todos configuráveis
  por `MAX_*` / `ANALYSIS_TIME_LIMIT_S` (ver `.env.example`).
- **GitHub fora do ar ou cota esgotada (ADR-013):** a análise falha com o motivo (HTTP 429/502) e fica
  registrada no histórico, sem marcar o repositório como inacessível.
- **Concorrência de análises (ADR-008):** uma análise em andamento por repositório (o segundo pedido recebe 409,
  garantido por um índice único no banco) e teto de análises síncronas por processo; sem vaga, a análise vai para a fila.
  Uma análise cujo worker caiu vira "falhou" sozinha depois de 15 min.
- **Recuperação de senha (ADR-005):** o endpoint só enfileira o pedido, então a resposta é igual — em conteúdo e em
  tempo — para qualquer e-mail; no máximo 3 pedidos por conta por hora.
- **E-mails** são comparados sem distinção de caixa; as respostas 429/413 levam CORS, para o navegador exibir a
  mensagem do servidor.
- **Código de terceiros nunca é executado:** o SoftMeter só lê o código-fonte e os relatórios de cobertura
  já publicados.

## 🏗️ Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.0 | Tipagem nativa, ecossistema científico (Radon, tree-sitter) |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS | Componentização, design system consistente |
| Banco de dados | PostgreSQL 16 | Robusto, relacional, suportado nas diretrizes do portfólio |
| Fila de tarefas | Celery + Redis | Análise assíncrona de repositórios grandes |
| Motor de métricas | Radon (CC/LOC/MI) + tree-sitter (JS/TS) | Bibliotecas especializadas por linguagem |
| Relatórios | ReportLab + Bitstream Vera TTF | PDF gerado server-side com Unicode |
| E-mail transacional | Resend (API HTTP) | Recuperação de senha; sem chave, o link vai para o log (ADR-005) |
| Testes | pytest + Jest + Testing Library + Playwright | TDD full-stack, cobertura ≥80% em CI; E2E rodado localmente |
| Container | Docker + Docker Compose | Ambiente local idêntico à produção |
| CI/CD | GitHub Actions | Lint + mypy + pytest + ESLint + Jest a cada push; Dependabot e auditoria de dependências semanais |

---

## 📐 O Framework Metrológico

### Analogia Metrologia Industrial × Software

| Metrologia Industrial | SoftMeter |
|---|---|
| Desenho técnico / GD&T | Catálogo de métricas (fórmula + limites) |
| Tolerância dimensional | Limite de especificação por métrica (nominal/superior) |
| Medição com Braço FARO | Análise automática do código-fonte via API do GitHub |
| Software PolyWorks | SoftMeter |
| Laudo de Inspeção | Laudo de Conformidade de Software (PDF) |
| Peça aprovada / refugada | Repositório Conforme / Não-Conforme |

### Classificação do Laudo

| Índice de Conformidade | Classificação |
|---|---|
| ≥ 90% | ✅ Conforme |
| 70% – 89% | ⚠️ Condicional |
| < 70% | ❌ Não-Conforme |

> **Como o índice é calculado:** média dos escores por métrica (Conforme = 100, Condicional = 50,
> Não-Conforme = 0). Uma métrica "Não disponível" (Cobertura de Testes sem fonte, ou Acoplamento quando
> nenhum import interno é resolvido) fica fora do cálculo — nunca conta como reprovação. Todas as
> métricas têm o mesmo peso.

> **Escopo da medição (ADR-011/012):** CC, LOC, Manutenibilidade, Acoplamento e Duplicação consideram
> apenas o **código-fonte de produção**. Arquivos de teste, dependências e arquivos gerados ou minificados
> ficam de fora (o dashboard e o PDF trazem essa nota). A Cobertura de Testes é lida dos relatórios
> publicados pelo próprio repositório — inclusive de monorepos, combinando os artifacts do mesmo run de CI.

---

## 📋 Documentação

- 📄 [RFC-001 — Documento de Proposta do Projeto](docs/rfc/RFC-001-SoftMeter-Avaliacao.md)
- 🏛️ [Decisões de Arquitetura (ADR)](docs/adr/)
- 🖼️ [Diagramas C4](docs/architecture/C4-diagramas.md)
- ☁️ [Roteiro de deploy público na AWS](docs/deploy/roteiro-deploy-aws.md)
- 🧭 [Especificação, plano e contratos da API](specs/001-softmeter-plataforma-mvp/) — os contratos em
  [`contracts/`](specs/001-softmeter-plataforma-mvp/contracts/) descrevem o comportamento real da API
  (a documentação interativa fica em <http://localhost:3001/docs>)
- 🤝 [Guia de contribuição](CONTRIBUTING.md)

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
