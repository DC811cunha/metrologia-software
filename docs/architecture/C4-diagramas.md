# Diagramas de Arquitetura — SoftMeter

> Atualizado em 05/11/2026 (RFC-001 v2.1). Reflete a arquitetura **implementada** — FastAPI/Python,
> conforme o [ADR-003](../adr/ADR-003-stack-backend-fastapi.md). A versão anterior deste arquivo
> descrevia a proposta original (Node.js + Express, domínio de sistemas/requisitos/ciclos/laudos),
> descontinuada no pivô de arquitetura; o código dessa época está em `docs/archive/backend-node-legacy/`.
> A descrição textual de cada componente está na seção 5 do
> [RFC-001](../rfc/RFC-001-SoftMeter-Avaliacao.md).

## Nível 1 — Diagrama de Contexto (C4)

```
┌──────────────────────────────────────────────────────────────────────┐
│                              SOFTMETER                               │
│              Plataforma de Metrologia de Qualidade de Software       │
│                                                                      │
│  ┌───────────────┐    ┌────────────────┐    ┌──────────────────────┐ │
│  │ Desenvolvedor │    │ Analista de QA │    │ Orientador/Avaliador │ │
│  │               │    │                │    │                      │ │
│  │ Cadastra      │    │ Consulta       │    │ Consulta laudos como │ │
│  │ repositórios  │    │ dashboards e   │    │ evidência técnica    │ │
│  │ e dispara     │    │ gera laudos    │    │ objetiva do código   │ │
│  │ análises      │    │ para revisão   │    │ entregue             │ │
│  └───────┬───────┘    └───────┬────────┘    └──────────┬───────────┘ │
│          └────────────────────┼────────────────────────┘             │
│                               ▼                                      │
│                    ┌─────────────────────┐                           │
│                    │  SoftMeter (Web App)│                           │
│                    └──────────┬──────────┘                           │
└───────────────────────────────┼──────────────────────────────────────┘
                                │
            ┌───────────────────┴────────────────────┐
            ▼                                        ▼
  ┌───────────────────────┐              ┌────────────────────────────┐
  │ API do GitHub         │              │ Resend (e-mail             │
  │ código-fonte (zipball)│              │ transacional) — v2.1       │
  │ linguagens, artifacts │              │ link de recuperação de     │
  │ de CI (cobertura)     │              │ senha; opcional (ADR-005)  │
  └───────────────────────┘              └────────────────────────────┘
```

Visitantes sem conta acessam apenas a página inicial pública (`/`). Os dados analisados são
sempre de repositórios GitHub **públicos**; o SoftMeter nunca executa código do repositório
analisado.

## Nível 2 — Diagrama de Containers (C4)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Usuário (Browser)                                                   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Frontend SPA — React 18 + TypeScript + Vite + Tailwind CSS    │  │
│  │  Porta: 3000                                                   │  │
│  │  Responsabilidade: telas, roteamento, gauges e gráficos        │  │
│  │  (Recharts), página inicial pública                            │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │ REST / JSON                              │
│  ┌────────────────────────▼───────────────────────────────────────┐  │
│  │  Backend API — FastAPI + Python 3.12                           │  │
│  │  Porta: 3001                                                   │  │
│  │  Responsabilidade: autenticação (JWT), orquestração da análise │  │
│  │  síncrona, classificação de conformidade, geração de PDF,      │  │
│  │  rate limiting dos endpoints de autenticação                   │  │
│  └────┬──────────────┬──────────────────┬─────────────────┬───────┘  │
│       │ SQL          │ enqueue          │ PDF             │ HTTPS    │
│  ┌────▼──────┐  ┌────▼──────────┐  ┌────▼──────────┐  ┌───▼───────┐  │
│  │PostgreSQL │  │ Redis         │  │ ReportLab     │  │ API GitHub│  │
│  │ 16        │  │ 7 (broker)    │  │ (biblioteca)  │  │ (externo) │  │
│  │ :5432     │  │ :6379         │  └───────────────┘  └───────────┘  │
│  └───────────┘  └────┬──────────┘                                    │
│                      │                                               │
│                 ┌────▼───────────────────────┐   HTTPS   ┌─────────┐ │
│                 │ Celery Worker              │──────────▶│ Resend  │ │
│                 │ • análise assíncrona       │           │(externo)│ │
│                 │   (repositórios grandes)   │           └─────────┘ │
│                 │ • envio do e-mail de       │                       │
│                 │   recuperação de senha     │                       │
│                 └────────────────────────────┘                       │
└──────────────────────────────────────────────────────────────────────┘
```

Os quatro serviços internos (`db`, `redis`, `backend`, worker) e o `frontend` sobem juntos com
`docker compose up --build`.

## Nível 3 — Diagrama de Componentes do Backend (C4)

```
Backend API (FastAPI) — src/backend/app/
│
├── api/                       → camada HTTP (rotas)
│   ├── auth.py                → registro, login, refresh, logout (JWT);
│   │                            forgot-password e reset-password
│   ├── repositories.py        → CRUD de repositórios + validação de linguagem
│   ├── analyses.py            → disparo de análise, consulta, histórico/tendência
│   └── reports.py             → geração e download do relatório PDF
│
├── analysis/                  → motor de métricas (núcleo de valor do produto)
│   ├── metrics_catalog.py     → catálogo fixo: fórmula, unidade, fonte, limites
│   ├── metric_engine.py       → Radon (Python) + tree-sitter (JS/TS): CC, LOC, MI
│   ├── coupling.py            → Instabilidade de Módulo (Martin, 2002)
│   ├── duplication.py         → shingling de tokens normalizados
│   └── coverage_reader.py     → artifact de CI → coverage.xml → lcov.info → badge
│
├── services/
│   ├── github_service.py      → API do GitHub (fallback sem token se o token for rejeitado)
│   ├── analysis_runner.py     → orquestra download + 6 métricas + persistência
│   ├── conformity_service.py  → classifica medições, calcula o índice agregado
│   ├── trend_service.py       → tendência entre as duas análises mais recentes
│   ├── report_service.py      → monta o PDF (ReportLab) com resumo interpretativo
│   └── email_service.py       → e-mail de recuperação: Resend, ou log se sem chave
│
├── workers/
│   ├── analysis_tasks.py      → task Celery de análise assíncrona
│   └── email_tasks.py         → task Celery send_password_reset_email_task
│
├── core/                      → configuração, segurança (JWT/bcrypt), dependências, Celery
├── db/                        → sessão SQLAlchemy
├── schemas/                   → modelos Pydantic de entrada/saída
├── models/                    → User, Repository, Analysis, Measurement, Report,
│                                PasswordResetToken (SQLAlchemy)
└── main.py                    → app FastAPI, CORS, limite de payload (64 KB) e rate limit
                                 (10/min/IP em /login, /forgot-password, /reset-password)
```

## Fluxo de Dados — Análise e Laudo de Conformidade

```
Usuário clica em "Executar análise"
        │
        ▼
POST /api/v1/repositories/{id}/analyses  (api/analyses.py)
  ├── Valida: repositório pertence ao usuário e está acessível
  ├── Cria Analysis (status: pendente → processando)
  └── Consulta o tamanho do repositório na API do GitHub
        │
        ├── tamanho ≤ limite síncrono ─────────────┐
        │                                          ▼
        │                          run_full_analysis (analysis_runner.py)
        │                            ├── baixa o código-fonte (zipball) — sem executá-lo
        │                            ├── calcula as 6 métricas (CC, LOC, MI,
        │                            │   Cobertura, Acoplamento, Duplicação)
        │                            ├── classifica cada medição: Conforme /
        │                            │   Condicional / Não-Conforme
        │                            └── persiste Measurements e o status geral
        │                                          │
        │                                          ▼
        │                              HTTP 201 com o resultado
        │
        └── tamanho > limite ──▶ HTTP 202 + task Celery (mesmo run_full_analysis)
                                  └── o frontend consulta o status a cada 2 s até concluir
        │
        ▼
Dashboard de Conformidade (6 gauges) ──▶ Histórico e Tendências
        │
        ▼
POST /api/v1/repositories/{id}/reports  (api/reports.py → report_service.py)
  ├── índice de conformidade (conformity_service.py): média dos escores por métrica
  │   avaliável (Conforme = 100, Condicional = 50, Não-Conforme = 0;
  │   "Não disponível" fica fora do cálculo)
  ├── classificação final: Conforme (≥ 90%) / Condicional (70–89%) / Não-Conforme (< 70%)
  ├── monta o PDF (resumo interpretativo + tabela com fórmula e fonte por métrica)
  └── persiste Report  ──▶  GET .../reports/{report_id}/download
```

## Fluxo de Dados — Recuperação de Senha (v2.1)

```
POST /auth/forgot-password  { e-mail }
  ├── e-mail NÃO cadastrado ──▶ resposta genérica imediata
  └── e-mail cadastrado
        ├── gera token (32 bytes), guarda só o hash SHA-256 (expira em 60 min)
        ├── enfileira send_password_reset_email_task ──▶ Celery ──▶ Resend (ou log)
        └── responde a MESMA mensagem genérica, no mesmo tempo (sem side-channel)

Usuário abre o link recebido ──▶ /reset-password?token=…
POST /auth/reset-password  { token, nova senha }
  ├── token inexistente, usado ou expirado ──▶ 400 "Token inválido ou expirado"
  └── token válido ──▶ atualiza o hash bcrypt da senha e marca o token como usado
```

## Modelo de Dados (DER simplificado)

```
users (1) ────────────── (N) repositories (1) ────────────── (N) analyses
  │                                │                                │
  │                                │                               (1)
  │                               (N)                               │
  │                             reports ◀──── (analise_id, opcional) │
  │                                                                (N)
  │                                                            measurements
  │
  └── (1) ───────────── (N) password_reset_tokens
```

Restrições relevantes: `UNIQUE(usuario_id, url)` em `repositories`; `token_hash` único em
`password_reset_tokens`. O catálogo das 6 métricas **não é tabela** — é código versionado
(`analysis/metrics_catalog.py`), por decisão do Princípio V da constituição do projeto.
