# Diagramas de Arquitetura — SoftMeter

> Atualizado em 18/11/2026 (revisão geral da documentação; inclui os ADRs 006–015). Reflete a arquitetura **implementada** — FastAPI/Python,
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
│  │  rate limit por IP e limite de corpo das requisições           │  │
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
│                 │ • pedido de recuperação de │                       │
│                 │   senha e envio do e-mail  │                       │
│                 └────────────────────────────┘                       │
└──────────────────────────────────────────────────────────────────────┘
```

Os quatro serviços internos (`db`, `redis`, `backend`, worker) e o `frontend` sobem juntos com
`docker compose up --build` (`docker-compose.yml`, **só para desenvolvimento**). Em produção usa-se o
`docker-compose.prod.yml` (ADR-007): sem portas de banco/Redis expostas, Redis com senha e o frontend
servido como build estático por um proxy reverso com HTTPS. O Redis, além de broker do Celery, pode
guardar os contadores do rate limit (`RATE_LIMIT_BACKEND=redis`, ADR-008; com timeout de 1 s, para cair para a
memória se não responder). A imagem de produção (`Dockerfile`, estágio `prod`) roda sem root e sem extras de teste, e os
PDFs ficam em um volume nomeado (`reports_data_prod`), que precisa de backup junto com o do Postgres (ADR-007). Versões
fixas em `src/backend/requirements.txt`; Dependabot e o workflow `audit.yml` acompanham as vulnerabilidades.

## Nível 3 — Diagrama de Componentes do Backend (C4)

```
Backend API (FastAPI) — src/backend/app/
│
├── api/                       → camada HTTP (rotas)
│   ├── auth.py                → registro, login, refresh, logout (JWT + cookie do refresh);
│   │                            forgot-password e reset-password
│   ├── repositories.py        → CRUD de repositórios + validação de linguagem; a exclusão
│   │                            apaga análises, medições, relatórios e os PDFs em cascata
│   ├── analyses.py            → disparo de análise, consulta, histórico/tendência; toda
│   │                            tentativa é registrada (inclusive as que falham); uma em
│   │                            andamento por repositório (409) e teto de análises síncronas
│   └── reports.py             → geração e download do relatório PDF
│
├── analysis/                  → motor de métricas (núcleo de valor do produto)
│   ├── metrics_catalog.py     → catálogo fixo: fórmula, unidade, fonte, limites
│   ├── metric_engine.py       → Radon (Python) + tree-sitter (JS/TS): CC, LOC, MI (média do
│   │                            repositório ponderada pelo SLOC); escopo só de código de produção
│   │                            (sem testes/gerados/minificados; build/dist/out/target/coverage
│   │                            só são podadas na raiz ou ao lado de um manifesto — ADR-015)
│   ├── coupling.py            → Instabilidade de Módulo (Martin, 2002); imports por sufixo
│   │                            de caminho (Python) e tsconfig/jsconfig com `extends` (JS/TS); sem aresta interna a
│   │                            métrica é "Não disponível", até com um módulo só (ADR-015)
│   ├── duplication.py         → shingling de tokens normalizados
│   ├── limits.py              → prazo cooperativo da análise (ADR-009)
│   └── coverage_reader.py     → artifacts de CI do run mais recente (combinados) →
│                                coverage.xml → lcov.info → badge
│
├── services/
│   ├── github_service.py      → API do GitHub: erros tipados (acesso negado, cota esgotada,
│   │                            indisponível, grande demais), segue redirects, fallback sem
│   │                            token se o token for rejeitado, limites de download/extração
│   ├── repository_sync.py     → alinha o cadastro ao GitHub (nome canônico, `github_id`,
│   │                            detecção de nome reaproveitado — ADR-014)
│   ├── analysis_runner.py     → orquestra download + 6 métricas + persistência
│   ├── stale_analyses.py      → encerra como `falhou` as análises que nunca terminam (worker
│   │                            caiu), ao listar/ler (ADR-013)
│   ├── sync_slots.py          → teto de análises síncronas por processo; sem vaga, vai para a
│   │                            fila (ADR-008)
│   ├── password_reset_service.py → token, limite por conta e e-mail da recuperação de senha,
│   │                            executado no worker (ADR-005)
│   ├── conformity_service.py  → classifica medições, calcula o índice agregado
│   ├── trend_service.py       → tendência entre as duas análises mais recentes
│   ├── report_service.py      → monta o Laudo PDF (ReportLab): veredito e índice, medidores,
│   │                            comparação com a análise anterior, resumo interpretativo,
│   │                            gráficos de evolução (histórico); usa report_theme.py
│   │                            (identidade visual, formatação) e report_charts.py (gráficos)
│   └── email_service.py       → e-mail de recuperação: Resend, ou log se sem chave
│
├── workers/
│   ├── analysis_tasks.py      → task Celery de análise assíncrona
│   ├── auth_tasks.py          → task Celery request_password_reset (o endpoint só enfileira)
│   └── email_tasks.py         → task Celery send_password_reset_email_task
│
├── core/                      → configuração (recusa iniciar em produção com padrões inseguros),
│                                segurança (JWT com `token_version`, bcrypt), dependências,
│                                rate_limit.py (memória ou Redis), Celery
├── db/                        → sessão SQLAlchemy
├── schemas/                   → modelos Pydantic de entrada/saída
├── models/                    → User, Repository, Analysis, Measurement, Report,
│                                PasswordResetToken (SQLAlchemy)
└── main.py                    → app FastAPI, limite de corpo (64 KB, contado em bytes) e rate limit
                                 (CORS é o middleware mais externo: cobre também os erros 413/429)
                                 por IP: login/forgot/reset 10/min; em produção
                                 também register 10/h, refresh 30/min e análises 20/h
```

## Fluxo de Dados — Análise e Laudo de Conformidade

```
Usuário clica em "Executar análise"
        │
        ▼
POST /api/v1/repositories/{id}/analyses  (api/analyses.py)
  ├── Valida: repositório pertence ao usuário
  ├── Encerra como `falhou` as análises perdidas do repositório (stale_analyses.py) e recusa
  │   com HTTP 409 se já houver uma `pendente`/`processando` (índice único parcial no banco)
  ├── Cria Analysis (status: pendente) — toda tentativa fica registrada
  ├── Consulta o repositório na API do GitHub (sempre; um repositório marcado como
  │   inacessível volta a ativo se responder)
  │     ├── 403/404/451 ─▶ análise `falhou` + HTTP 409; repositório vira `inacessivel`
  │     ├── cota esgotada ─▶ `falhou` + HTTP 429 (Retry-After); repositório segue ativo
  │     └── GitHub fora do ar ─▶ `falhou` + HTTP 502; repositório segue ativo
  ├── Sincroniza a identidade (repository_sync.py): renomeado → atualiza url/nome;
  │   nome reaproveitado por outro repositório → `falhou` + HTTP 409
  └── Confere o tamanho: acima de 200 MB → `falhou` + HTTP 422
        │
        ├── tamanho ≤ limite síncrono (5000 KB) E há vaga (sync_slots.py) ──┐
        │                                          ▼
        │                          run_full_analysis (analysis_runner.py)
        │                            ├── baixa o código-fonte (zipball) — sem executá-lo —
        │                            │   com tetos de download/extração e prazo de 300 s
        │                            ├── calcula as 6 métricas (CC, LOC, MI,
        │                            │   Cobertura, Acoplamento, Duplicação)
        │                            ├── classifica cada medição: Conforme /
        │                            │   Condicional / Não-Conforme
        │                            └── persiste Measurements e o status geral
        │                                          │
        │                                          ▼
        │                              HTTP 201 com o resultado (`concluida` — ou `falhou`,
        │                              com `motivo_falha`, se o pipeline falhar)
        │
        └── tamanho > limite OU sem vaga síncrona ──▶ HTTP 202 + task Celery (mesmo run_full_analysis)
                                  ├── fila indisponível ─▶ `falhou` + HTTP 503
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

## Fluxo de Dados — Sessão e Logout (ADR-006)

```
Login / cadastro ──▶ access token (15 min, corpo da resposta) + refresh token (7 dias, só no
                     cookie HttpOnly `softmeter_refresh_token`); ambos carregam a `token_version`
POST /auth/refresh ─▶ lê o cookie; recusa token de versão antiga (401)
POST /auth/logout  ─▶ identifica a sessão pelo cookie do refresh (ou pelo access token), sobe a
                      `token_version` do usuário e apaga o cookie; é idempotente (204 mesmo sem
                      sessão válida). Reset de senha também sobe a versão.
                      ⇒ derruba access e refresh tokens de todos os dispositivos, na hora.
```

## Fluxo de Dados — Recuperação de Senha (v2.1)

```
POST /auth/forgot-password  { e-mail }
  ├── só enfileira request_password_reset(e-mail) e responde a MESMA mensagem genérica —
  │   sem consultar o banco, então o tempo não depende de a conta existir (ADR-005)
  └── no worker (password_reset_service.py):
        ├── e-mail NÃO cadastrado ──▶ nada
        └── e-mail cadastrado
              ├── limite de 3 pedidos por conta por hora (excedentes ignorados em silêncio)
              ├── gera token (32 bytes), guarda só o hash SHA-256 (expira em 60 min) e remove
              │   tokens usados/vencidos há mais de 1 h
              └── envia o link ──▶ Resend (ou log se não houver chave)

Usuário abre o link recebido ──▶ /reset-password?token=…
POST /auth/reset-password  { token, nova senha }
  ├── token inexistente, usado ou expirado ──▶ 400 "Token inválido ou expirado"
  └── token válido ──▶ atualiza o hash bcrypt da senha e marca o token como usado
```

## Modelo de Dados (DER simplificado)

```
users (1) ────────────── (N) repositories (1) ────────────── (N) analyses
(token_version, e-mail       (github_id, URL               (no máx. 1 em andamento
 em minúsculas)              normalizada)                  por repositório — índice parcial)
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
`password_reset_tokens`. Excluir um repositório apaga, em cascata, suas análises, medições e relatórios
(e os arquivos PDF no disco). O catálogo das 6 métricas **não é tabela** — é código versionado
(`analysis/metrics_catalog.py`), por decisão do Princípio V da constituição do projeto.
