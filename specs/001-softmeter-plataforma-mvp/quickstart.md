# Quickstart: SoftMeter — Plataforma de Metrologia de Qualidade de Software

**Feature**: 001-softmeter-plataforma-mvp | **Date**: 2026-06-24 | **Atualizado**: 2026-11-05 (recuperação de senha, E2E)

## Pré-requisitos

- Docker e Docker Compose
- Node.js 20+ (apenas para o frontend Vite local, fora do container)
- Python 3.12 (apenas se for rodar o backend fora do container)

## Setup local

```bash
# 1. Subir o ambiente completo (PostgreSQL, Redis, backend FastAPI, worker Celery, frontend)
docker compose up --build -d

# 2. Aplicar migrations do banco (apenas na primeira execução ou após novas migrations)
docker compose exec backend alembic upgrade head
```

A aplicação estará disponível em:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:3001 (Swagger/OpenAPI em `/docs`)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Fluxo de validação manual (User Story 1 + 2)

1. Acessar o frontend e criar uma conta (`POST /api/v1/auth/register`).
2. Cadastrar um repositório GitHub público Python ou JS/TS (ex.:
   `https://github.com/pallets/flask`).
3. Disparar uma análise e aguardar o resultado (síncrono em até ~10s, ou polling se assíncrono).
4. Verificar que o dashboard exibe as 6 métricas como gauges com valor, limites e status de
   conformidade.
5. Repetir o passo 3 em outro dia/momento e confirmar que o histórico (US3) mostra a tendência.
6. Gerar um relatório PDF (US4) e confirmar que cada métrica inclui fórmula, fonte bibliográfica
   e limites.

## Validação manual — recuperação de senha (ADR-005)

1. Na tela de login, clicar em "Esqueci minha senha" (`/forgot-password`) e informar o e-mail
   cadastrado — e, em outra tentativa, um e-mail inexistente: a mensagem exibida deve ser a mesma
   nos dois casos.
2. Sem `RESEND_API_KEY`, o link de redefinição aparece no log do worker Celery:
   `docker compose logs celery-worker | grep reset-password`. Abrir o link
   (`/reset-password?token=…`), definir uma nova senha (mín. 8 caracteres) e fazer login com ela.
3. Reabrir o mesmo link: deve ser recusado ("Token inválido ou expirado") — o token é de uso único
   e expira em 60 minutos.

> O `.env` é opcional. `GITHUB_TOKEN` habilita a leitura de cobertura via artifact do GitHub
> Actions (ADR-004) e `RESEND_API_KEY` o envio real do e-mail (ADR-005); sem eles, o sistema segue
> funcionando com os fallbacks documentados.

## Rodando os testes

```bash
# Backend (cria venv local primeiro, se ainda não existir)
cd src/backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest --cov=app --cov-report=term-missing

# Frontend
cd src/frontend
npm install
npm test

# E2E (requer a aplicação rodando em localhost:3000 — ver tests/e2e/README.md)
cd tests/e2e
npm install
npx playwright install --with-deps chromium   # apenas na primeira vez
npm test
```

## Critério de pronto (alinhado à Constitution Check do plan.md)

- Cobertura ≥ 80% em backend e frontend (Princípio I)
- Testes unitário + integração + E2E passando em CI (Princípio II)
- Dashboard usando o componente único de gauge para as 6 métricas (Princípio III)
- Análise síncrona completando em até 10s para repositórios pequenos/médios (Princípio IV)
- Todas as 6 métricas com entrada completa no catálogo (`data-model.md`) antes de aparecerem na
  UI (Princípio V)
