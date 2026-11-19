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

## Atualização (18/11/2026): imagem de produção, volume dos PDFs e dependências

Da revisão geral de 18/11/2026:

- **Imagem de produção separada.** O `Dockerfile` do backend ganhou os estágios `prod` e `dev` (o padrão). O `prod`
  instala só as dependências de execução, não tem `--reload` e roda como usuário sem privilégios (uid 10001; o
  Celery já avisava que rodava como root). O `docker-compose.prod.yml` usa `target: prod`.
- **Volume para os PDFs.** Sem volume, os relatórios moravam no sistema de arquivos do container e sumiam a cada
  recriação (deploy ou atualização de imagem); todo relatório antigo passava a dar 404. Agora `REPORTS_DIR` aponta
  para `/app/generated_reports`, montado no volume nomeado `reports_data_prod` (verificado: o arquivo sobrevive à
  recriação do container e é gravável pelo usuário sem privilégios). **Faça backup desse volume junto com o do
  Postgres.**
- **Builds reprodutíveis.** `src/backend/requirements.txt` fixa todas as versões (usado por Docker e CI com `-c`);
  o CI do frontend passou a usar `npm ci`. Dependabot semanal e o workflow `audit.yml` (`pip-audit`/`npm audit`)
  cuidam das atualizações e dos alertas.
- **Redis do limitador com timeout** (1 s): um Redis que aceita a conexão e não responde fazia cada requisição
  esperar o tempo padrão do TCP em vez de cair para o limite em memória (ADR-008).
- **Vulnerabilidades do frontend: zero.** O `npm audit fix` resolveu `axios` e `follow-redirects`; sobravam avisos que
  exigiam versão maior — `react-router` 6 (redirecionamento aberto em `<Link>`/`useNavigate` com URL controlada pelo
  usuário e hidratação SSR; o app só usa rotas fixas) e, só em desenvolvimento, `vite`/`esbuild` 5 e `minimatch` via
  `@typescript-eslint` 6. Foram atualizados em seguida para `react-router-dom` 7, `vite` 7 (com `@vitejs/plugin-react` 5)
  e `@typescript-eslint` 8. O que a troca exigiu foi pouco: um polyfill de `TextEncoder` no `jest.setup.ts` (o
  `react-router` 7 o usa e o jsdom não o fornece), trocar uma interface vazia por um tipo (regra nova do ESLint) e o
  `engines` do `package.json` (`node >= 20.19`, exigência do vite 7). Verificado com a suíte E2E completa (15/15) contra
  a stack Docker com as versões novas.

## Atualização (19/11/2026): Vite 8, plugin-react 6 e o `.dockerignore` do frontend

O Dependabot propôs o Vite 8 e, em seguida, o `@vitejs/plugin-react` 6 (que exige o Vite 8). Ambos foram adotados depois de
testar de verdade — build, servidor de desenvolvimento e a suíte E2E completa (15/15) contra a stack Docker —, com `npm audit`
zerado. O CI passou a **construir o frontend** (`npm run build`): o PR do Tailwind 4 tinha passado verde nos testes mesmo
quebrando o build.

Reconstruir o container do frontend depois do Vite 8 revelou um problema antigo: `src/frontend` não tinha `.dockerignore`, então
o `COPY . .` do Dockerfile copiava o `node_modules` **do host** (versões e binários do Windows) por cima das dependências que a
imagem acabara de instalar — o container rodava o Vite 7 antigo e falhava com `Cannot find module @rollup/rollup-linux-x64-musl`.
O `.dockerignore` (`node_modules`, `dist`, `coverage`) resolve.

O frontend também migrou para o **ESLint 9** (formato flat, `eslint.config.js`; o `.eslintrc.cjs` e a opção `--ext` deixaram de existir), com
`typescript-eslint` 8 e `eslint-plugin-react-hooks` 5 — as mesmas regras de antes, conferidas com um arquivo de sonda (hook condicional,
dependência faltando, `debugger`, `any`, variável sem uso). A v7 do `react-hooks` e o ESLint 10 ficam para depois: a primeira acrescenta regras
que apontam trechos do nosso código.

Ficaram de fora, por exigirem migração própria: React 19, ESLint 10, `eslint-plugin-react-hooks` 7, Tailwind 4, TypeScript 7, Babel 8,
`eslint-plugin-react-hooks` 7 e Jest 30 (que traz `glob`/`minimatch` com avisos de segurança em dev).

## Consequências

- O deploy público precisa gerar segredos próprios (`python -c "import secrets; print(secrets.token_urlsafe(48))"`)
  e servir a API por HTTPS (`COOKIE_SECURE=true`).
- O compose de produção cobre backend, worker, Postgres e Redis; o **frontend** deve ser servido como
  build estático pelo proxy reverso (a definir junto com a hospedagem).
- O Redis do compose de produção tem senha, mas ainda é usado apenas como broker/backend do Celery; o
  rate limit (issue #98) é tratado separadamente.
