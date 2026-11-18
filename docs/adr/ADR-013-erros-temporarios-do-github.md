# ADR-013: Erros Temporários do GitHub (cota esgotada e indisponibilidade)

**Data:** 08/11/2026
**Status:** Aceito
**Autor:** Diego Cunha
**Origem:** revisão por pares do Sandro Machiniski — issues #90 e #91 (ambas reproduzidas antes de corrigir)

---

## Contexto

O `GithubService` só distinguia dois mundos: sucesso ou `RepositoryAccessError` (404/403). Isso produzia:

- **#90:** o GitHub usa `403` (e às vezes `429`) também para **limite de requisições**, primário
  (`x-ratelimit-remaining: 0`) e secundário (`retry-after` ou mensagem). Esse 403 virava "repositório
  inacessível", e nada devolvia o repositório ao estado ativo: um pico de uso o deixava bloqueado para sempre,
  mesmo sendo público e existente.
- **#91:** timeout, conexão recusada, `429` e `5xx` chegavam como exceções cruas do `httpx` e viravam erro 500.
  Como a `Analysis` já estava gravada como `PENDENTE` antes da chamada, ela ficava presa nesse estado (e a de
  `PROCESSANDO`, se o Redis estivesse fora do ar). Cada requisição criava um `GithubService` e nunca o fechava.

## Decisão

- **Erros tipados.** `GithubRateLimitError` (com `retry_after`) e `GithubUnavailableError`, ambos
  *temporários*. Uma única função classifica toda resposta de erro do GitHub: cota esgotada (429, ou 403 com
  sinal de limite) → `GithubRateLimitError`; 403/404/451 sem sinal de limite → `RepositoryAccessError`; qualquer
  outro status (5xx, inesperado) e falhas de transporte (inclusive no meio do download em streaming) →
  `GithubUnavailableError`.
- **`Retry-After`** vem do cabeçalho `retry-after` ou, na falta, de `x-ratelimit-reset`. O handler global de
  `HTTPException` passou a **preservar os cabeçalhos** (antes os descartava).
- **API:** cadastro e análise respondem `429` (com `Retry-After`) para cota esgotada e `502` para indisponibilidade
  do GitHub, com mensagens em português; fila fora do ar responde `503`. Em todos os casos a análise é gravada como
  `falhou` **com o motivo** — nunca fica `pendente`/`processando` — e o repositório **continua ativo**.
- **Auto-cura.** O bloqueio antecipado de repositório inacessível foi removido: a análise sempre consulta o
  GitHub e, se o repositório responder, ele volta a `ativo` (isso também corrige repositórios já marcados por
  engano). Um repositório que de fato sumiu continua virando `inacessível` (409).
- **Ciclo de vida:** o cliente HTTP é fechado ao fim de cada requisição, do pipeline e da task Celery.
- **Frontend:** a tela mostra a mensagem do servidor para 409/422/429/502/503 em vez de "Não foi possível
  executar a análise".

## Justificativa

- **Cota esgotada e indisponibilidade não dizem nada sobre o repositório**: tratá-las como acesso negado
  transforma um problema temporário em um estado permanente.
- **Uma só função de classificação** evita que cada chamada repita (e erre) a lista de status.
- **Falhar com motivo** é melhor que não registrar: o histórico mostra o que aconteceu e o usuário sabe quando tentar de novo.

## Consequências

- Uma análise de repositório marcado como inacessível agora custa uma chamada ao GitHub (antes, nenhuma). O rate
  limit por IP em produção (ADR-008) limita o abuso.
- Cada tentativa que falha por cota ou indisponibilidade gera um registro `falhou` no histórico do repositório.
- A cobertura via artifacts continua "melhor esforço": nenhum desses erros a derruba nem aparece para o usuário.
- Não há retry automático: a mensagem informa quando tentar de novo, mas a nova tentativa é do usuário.

## Atualização (17/11/2026): falhas têm data de término

Ao conferir os contratos da API verificou-se que as falhas gravadas pela rota (`_fail_analysis`: 409, 429, 502, 503) não
preenchiam `concluida_em`, ao contrário das falhas do pipeline. A tela de histórico mostrava essas tentativas como
"Em andamento", e o item do histórico não trazia `status` para distingui-las. Corrigido: toda falha grava `concluida_em`
(uma migração preencheu as já existentes com `solicitada_em`), o item do histórico passa a incluir `status`,
`motivo_falha` e `solicitada_em`, a tela mostra "Falhou" com o motivo, e um erro inesperado ao disparar a análise também a
marca como `falhou` em vez de deixá-la `pendente`.

## Atualização (18/11/2026): análises perdidas e tela

Uma análise cujo worker caiu (a tarefa é confirmada antes de executar) ficava `processando` para sempre, e o
polling da tela era um laço infinito. Agora (a) as consultas que listam ou leem análises marcam como `falhou`
as que passam de `STALE_ANALYSIS_AFTER_S` (900 s) sem terminar — sem processo agendado, para não acrescentar
uma peça ao deploy; (b) o worker descarta em silêncio o resultado de uma análise cujo repositório foi
excluído durante a execução (antes: `StaleDataError` com traceback); (c) o polling tem tempo máximo (10 min),
cancela ao sair da tela e tolera falhas de rede curtas; (d) o dashboard reconsulta uma análise em andamento.
A lista de repositórios também passou a (e) manter os links do dashboard e do histórico após uma tentativa
que falhou (`ultima_concluida_id`), (f) permitir executar a análise de um repositório `inacessivel` — que
esta mesma decisão manda reativar quando ele responder — e (g) rotular o estado de acesso como
"Inacessível" em vez de "Não-Conforme".
