# Quickstart: SoftMeter — Plataforma de Metrologia de Qualidade de Software

**Feature**: 001-softmeter-plataforma-mvp | **Date**: 2026-06-24

## Pré-requisitos

- Docker e Docker Compose
- Node.js 20+ (apenas para o frontend Vite local, fora do container)
- Python 3.12 (apenas se for rodar o backend fora do container)

## Setup local

```bash
# 1. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com: DATABASE_URL, REDIS_URL, JWT_SECRET, JWT_REFRESH_SECRET

# 2. Subir o ambiente completo (PostgreSQL, Redis, backend FastAPI, worker Celery, frontend)
docker-compose up --build

# 3. Aplicar migrations do banco
docker-compose exec backend alembic upgrade head
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

## Rodando os testes

```bash
# Backend
cd src/backend
pip install -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing

# Frontend
cd src/frontend
npm install
npm test

# E2E
npx playwright test
```

## Critério de pronto (alinhado à Constitution Check do plan.md)

- Cobertura ≥ 80% em backend e frontend (Princípio I)
- Testes unitário + integração + E2E passando em CI (Princípio II)
- Dashboard usando o componente único de gauge para as 6 métricas (Princípio III)
- Análise síncrona completando em até 10s para repositórios pequenos/médios (Princípio IV)
- Todas as 6 métricas com entrada completa no catálogo (`data-model.md`) antes de aparecerem na
  UI (Princípio V)
