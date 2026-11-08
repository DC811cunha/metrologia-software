# ADR-007: Configuração Segura de Produção (recusar iniciar com padrões inseguros)

**Data:** 08/11/2026
**Status:** Aceito
**Autor:** Diego Cunha
**Origem:** revisão por pares do Sandro Machiniski — issue #97

---

## Contexto

Os segredos JWT e a senha do banco tinham valores padrão no código, no `docker-compose.yml` e no
`.env.example` — todos em um **repositório público**. Quem esquecesse de definir as variáveis em
produção publicaria um sistema cujos tokens qualquer pessoa consegue forjar, sem nenhum aviso. O
`docker-compose.yml`, pensado para desenvolvimento, também publica Postgres (`5432`) e Redis
(`6379`, sem senha) em todas as interfaces e roda o backend com `--reload`, e nada separava esse uso
do de produção.

## Decisão

- Nova configuração `ENVIRONMENT` (`development` por padrão, ou `production`).
- Com `ENVIRONMENT=production`, `Settings` **falha na criação** — e portanto a API não inicia — se:
  `JWT_SECRET` ou `JWT_REFRESH_SECRET` forem algum valor de exemplo do repositório ou tiverem menos
  de 32 caracteres; se os dois forem iguais; se `COOKIE_SECURE` não for `true`; ou se `DATABASE_URL`
  usar a senha padrão. Todos os problemas são listados de uma vez.
- Novo `docker-compose.prod.yml`: sem portas de Postgres/Redis, Redis com senha, sem `--reload` nem
  volume de código, backend escutando só em `127.0.0.1` (o proxy reverso com HTTPS o expõe) e toda
  credencial **obrigatória** (`${VAR:?mensagem}`): o `compose` recusa subir se faltar alguma.
- `FORWARDED_ALLOW_IPS` obrigatório no compose de produção, para o uvicorn confiar no
  `X-Forwarded-For` apenas do proxy reverso.
- README separa explicitamente desenvolvimento e produção.

## Justificativa

- **Falhar alto e cedo** é mais seguro que um aviso em log: a configuração insegura nunca chega a
  atender requisições.
- **Opt-in por `ENVIRONMENT`:** desenvolvimento, testes e CI continuam funcionando com os padrões, sem
  fricção; a rigidez só vale onde importa.
- **Lista fixa de valores conhecidos** (além do tamanho mínimo): os placeholders do `.env.example` têm
  mais de 32 caracteres e passariam numa checagem só de comprimento.

## Consequências

- O deploy público precisa gerar segredos próprios (`python -c "import secrets; print(secrets.token_urlsafe(48))"`)
  e servir a API por HTTPS (`COOKIE_SECURE=true`).
- O compose de produção cobre backend, worker, Postgres e Redis; o **frontend** deve ser servido como
  build estático pelo proxy reverso (a definir junto com a hospedagem).
- O Redis do compose de produção tem senha, mas ainda é usado apenas como broker/backend do Celery; o
  rate limit (issue #98) é tratado separadamente.
