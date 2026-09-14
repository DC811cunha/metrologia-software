# Testes E2E — SoftMeter (Playwright)

Cobrem os fluxos críticos ponta a ponta pela UI real (`research.md` item 10, `plan.md`),
um arquivo por user story:

| Arquivo | User Story | Task |
|---|---|---|
| `cadastro_analise.spec.ts` | US1 — Cadastro + análise | T030 |
| `dashboard_gauges.spec.ts` | US2 — Dashboard de gauges | T046 |
| `historico_tendencia.spec.ts` | US3 — Histórico e tendência | T051 |
| `relatorio_pdf.spec.ts` | US4 — Relatório PDF | T058 |
| `autenticacao.spec.ts` | US5 — Autenticação | T064 |

Os fluxos de US1–US4 cadastram e analisam `github.com/pypa/sampleproject` (pequeno,
Python, estável) — a suíte bate na API real do GitHub sem autenticação, então respeita
o limite de 60 requisições/hora por IP; `fullyParallel: false` no `playwright.config.ts`
evita disparar essas chamadas em paralelo.

## Pré-requisitos

A aplicação completa precisa estar rodando **antes** de disparar os testes — esta
suíte não sobe backend/frontend sozinha (ver nota em `playwright.config.ts`):

```bash
# a partir da raiz do repositório
docker compose up --build -d
docker compose exec backend alembic upgrade head
```

Alternativa sem Docker (útil para depuração local — mesma app, sem Postgres/Redis
reais; o path síncrono de análise não depende deles para um repositório pequeno):

```bash
# backend, em um terminal (SQLite local em vez de Postgres)
cd src/backend
.venv/Scripts/activate  # Linux/Mac: source .venv/bin/activate
DATABASE_URL=sqlite:///./e2e.db JWT_SECRET=<=32 chars> JWT_REFRESH_SECRET=<=32 chars> \
  alembic upgrade head
DATABASE_URL=sqlite:///./e2e.db JWT_SECRET=<mesmo valor> JWT_REFRESH_SECRET=<mesmo valor> \
  uvicorn app.main:app --port 3001

# frontend, em outro terminal
cd src/frontend
VITE_API_URL=http://localhost:3001 npm run dev
```

## Rodando os testes

```bash
cd tests/e2e
npm install
npx playwright install --with-deps chromium   # apenas na primeira vez
npm test
```

`E2E_BASE_URL` sobrepõe a URL do frontend (padrão `http://localhost:3000`) se a
aplicação estiver em outra porta/host.
