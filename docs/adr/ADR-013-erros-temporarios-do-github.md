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
