# ADR-008: Rate Limit Compartilhado e Limite de Corpo Real

**Data:** 08/11/2026
**Status:** Aceito
**Autor:** Diego Cunha
**Origem:** revisão por pares do Sandro Machiniski — issue #98

---

## Contexto

O rate limit original (`_login_window` em `main.py`) tinha cinco limitações, todas relevantes para um
deploy público:

1. Usava `request.client.host`: atrás de um proxy reverso, todos os usuários chegariam com o IP do
   proxy e dividiriam os mesmos 10 pedidos por minuto.
2. O estado vivia na memória de cada processo: com N workers/réplicas o limite efetivo seria `N × 10`
   e zerava a cada deploy.
3. As chaves `path:ip` nunca eram removidas do dicionário, que só crescia.
4. Não cobria `/register`, `/refresh` nem a criação de análises — cada análise consome a cota do
   GitHub do sistema inteiro e CPU do servidor.
5. O limite de corpo (64 KB) só olhava o cabeçalho `Content-Length`; requisições com
   `Transfer-Encoding: chunked` não o têm e passavam sem limite.

## Decisão

- Novo módulo `app/core/rate_limit.py` com dois backends de mesma interface:
  - **memória** (padrão): janela deslizante por processo, com varredura periódica de chaves ociosas;
  - **Redis** (`RATE_LIMIT_BACKEND=redis`): contador por janela fixa (`INCR` + `EXPIRE`), compartilhado
    entre processos e réplicas, que expira sozinho. Se o Redis falhar, cai para a memória (com aviso),
    em vez de derrubar a API ou deixar de limitar.
- Regras: login, forgot-password e reset-password sempre (10/min por IP). Em **produção**
  (`ENVIRONMENT=production`): `/register` (10/hora), `/refresh` (30/min) e criação de análises
  (20/hora), todos por IP e configuráveis (`RATE_LIMIT_*`).
- IP atrás de proxy: não se lê `X-Forwarded-For` no código. O `docker-compose.prod.yml` sobe o
  uvicorn com `--proxy-headers` e `FORWARDED_ALLOW_IPS` obrigatório (só o proxy confiável é
  considerado), e `request.client.host` já reflete o cliente real.
- Limite de corpo reescrito como middleware ASGI que **conta os bytes recebidos**, além de conferir o
  `Content-Length`. Como o FastAPI converte exceções da leitura do corpo em 400, o 413 é enviado no
  próprio middleware assim que o limite estoura.

## Justificativa

- **Redis opcional, não padrão:** o projeto já o usa (Celery), mas desenvolvimento, testes e CI não
  devem depender dele para o rate limit; um backend configurável mantém tudo simples localmente.
- **Janela fixa no Redis:** é atômica com um `INCR` e não exige scripts Lua; a imprecisão nas bordas
  da janela é aceitável para limites contra abuso.
- **Limites estendidos só em produção:** criar várias contas e análises em sequência é o fluxo normal
  de desenvolvimento e dos testes E2E; limitar isso ali só atrapalharia.
- **Não confiar em `X-Forwarded-For` por conta própria:** qualquer cliente pode forjar o cabeçalho,
  o que permitiria burlar o limite; a confiança é delegada ao servidor ASGI, restrita ao proxy.

## Consequências

- O limite por IP penaliza usuários atrás de um mesmo NAT (ex.: uma sala de aula analisando
  repositórios); os valores são configuráveis para ajuste.
- A regra de análises é por IP, não por usuário nem por repositório (o middleware roda antes da
  autenticação). Uma análise ativa por repositório fica como melhoria possível.
- No deploy público, definir `RATE_LIMIT_BACKEND=redis` (já no `docker-compose.prod.yml`) e
  `FORWARDED_ALLOW_IPS` com o IP/rede do proxy reverso.
