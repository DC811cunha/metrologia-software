# Contract: Análises

**Feature**: 001-softmeter-plataforma-mvp | Requisitos: FR-003 a FR-008, FR-012, FR-014, US1, US2, US3

Base path: `/api/v1/repositories/{repository_id}/analyses` (autenticado; repositório deve
pertencer ao usuário — FR-011)

## Convenções comuns

*(Atualizado em 17/11/2026 — ADR-008, ADR-009, ADR-011 e ADR-014; reflete o comportamento atual.)*

- **Sem token válido** → `401 {"detail": "Não autenticado"}`. Repositório ou análise de outro usuário →
  `404` (FR-011).
- **Erros de negócio** têm o corpo `{"detail": "<mensagem em português>"}` — **não** existe `motivo_falha`
  no corpo de erro; esse campo só aparece dentro do objeto **Análise** (abaixo).
- **IDs que não são UUID** e demais erros de schema → `422` com `detail` em lista (formato FastAPI).

## Objeto Análise

```json
{
  "id": "uuid",
  "repositorio_id": "uuid",
  "status": "pendente | processando | concluida | falhou",
  "motivo_falha": "string | null",
  "solicitada_em": "timestamp",
  "concluida_em": "timestamp | null",
  "status_conformidade_geral": "Conforme | Condicional | Não-Conforme | null",
  "medicoes": [
    { "metrica_chave": "string", "valor_medido": 12.5, "status_conformidade": "Conforme | Condicional | Não-Conforme | Não disponível" }
  ]
}
```

`status_conformidade_geral` é `null` até a análise concluir; é a média dos scores das medições
(**excluindo** as "Não disponível"; se nenhuma tiver score, vale "Não-Conforme").

`valor_medido` é `null` quando a métrica **não pôde ser calculada** (ex.: acoplamento em um projeto sem
imports internos resolvíveis, ou cobertura sem relatório publicado) — a medição aparece como "Não
disponível" e não entra no cálculo da conformidade geral.

**Escopo da medição (ADR-011):** as métricas consideram apenas código-fonte de produção em Python,
JavaScript e TypeScript; ficam **fora** testes, código gerado e arquivos minificados. O PDF e o dashboard
exibem essa nota de escopo.

## POST /api/v1/repositories/{repository_id}/analyses

Dispara uma nova análise sob demanda (FR-003, FR-012 — sem agendamento automático).

**Comportamento**: baixa o conteúdo do repositório (ver `research.md` item 1), calcula as 6 métricas do
catálogo (`data-model.md`). Se o tamanho do repositório estiver dentro do orçamento síncrono
(`sync_analysis_size_limit_kb`, padrão **5 000 KB**), devolve o resultado completo; acima disso, devolve
`processando` e a análise termina de forma assíncrona via Celery/Redis (Princípio IV).

**Toda tentativa é registrada**: mesmo quando falha, a análise é gravada com `status = falhou`, o
`motivo_falha` e a data de término (`concluida_em`), e continua visível no histórico.

**Efeitos colaterais**: pode atualizar `url`/`owner_nome` do repositório se ele foi renomeado e gravar o
`github_id` (ver *Identidade do repositório* em `repositories.md`); se o GitHub negar o acesso (403, 404
ou 451), marca o repositório como `inacessivel`, e volta a `ativo` na primeira análise que o GitHub
voltar a servir — não há bloqueio antecipado por estar `inacessivel`.

**Responses**:
- `201 Created` → objeto **Análise** completo com as 6 medições. **Atenção:** `status` pode ser
  `concluida` **ou `falhou`** — uma falha do pipeline no caminho síncrono (ex.: arquivo ilegível) também
  responde `201`, com `motivo_falha` preenchido e `medicoes` vazia. O cliente deve olhar o `status`.
- `202 Accepted` → `{ "id": "uuid", "status": "processando" }`; consultar por polling em
  `GET …/analyses/{analysis_id}`
- `404 Not Found` → `"Repositório não encontrado"`
- `409 Conflict` (`detail` + análise registrada como `falhou`):
  - acesso negado pelo GitHub → repositório inexistente, privado ou bloqueado (FR-014);
  - o nome cadastrado passou a apontar para **outro** repositório →
    `"O endereço cadastrado (…) agora aponta para outro repositório do GitHub. Remova este cadastro e cadastre o repositório novamente."`
- `422 Unprocessable Entity` → repositório acima do limite absoluto (`max_repo_size_kb`, padrão 200 MB):
  `"Repositório grande demais para análise (X MB; máximo Y MB)"` (ADR-009)
- `429 Too Many Requests` → cota da API do GitHub esgotada (com `Retry-After` quando informado) **ou**,
  em produção, mais de **20 análises por hora por IP** (ADR-008)
- `502 Bad Gateway` → `"O GitHub está indisponível no momento. Tente novamente em instantes."`
- `503 Service Unavailable` → `"Não foi possível enfileirar a análise agora. Tente novamente em instantes."`
  (fila Celery/Redis fora do ar; só no caminho assíncrono)

## GET /api/v1/repositories/{repository_id}/analyses/{analysis_id}

Consulta o status/resultado de uma análise (usado para polling enquanto `status = processando`).

**Responses**:
- `200 OK` → objeto **Análise**: `concluida` traz `status_conformidade_geral` e as medições; `falhou`
  traz `motivo_falha`; `processando` traz só o status, sem medições
- `404 Not Found` → `"Análise não encontrada"` (inexistente, de outro repositório ou de outro usuário)

## GET /api/v1/repositories/{repository_id}/analyses

Lista o histórico de análises do repositório em **ordem cronológica** (FR-008, US3).

**Sem filtro**: devolve **todas** as tentativas — inclusive `falhou` e `processando` — em itens
reduzidos:

```json
[{
  "id": "uuid",
  "status": "pendente | processando | concluida | falhou",
  "motivo_falha": "string | null",
  "solicitada_em": "timestamp",
  "concluida_em": "timestamp | null",
  "status_conformidade_geral": "…|null",
  "medicoes": []
}]
```

`concluida_em` é a data de **término**, e toda tentativa encerrada a tem — inclusive as que `falharam`
(a falha é o término). Só `pendente`/`processando` a têm `null`; o cliente deve decidir "em andamento"
pelo `status`, não pela ausência da data. `medicoes` vem vazia nas tentativas que não concluíram.

**Com `?metrica={chave}`**: devolve a série temporal de uma única métrica:

```json
{
  "metrica_chave": "string",
  "tendencia": "melhorando | piorando | estavel | null",
  "serie": [
    { "analise_id": "uuid", "concluida_em": "timestamp", "valor_medido": 12.5, "status_conformidade": "Conforme" }
  ]
}
```

- A `serie` contém **somente análises concluídas**, em ordem cronológica.
- `tendencia` compara os **dois últimos pontos** da série; vale `null` quando há menos de 2 pontos ou
  algum dos valores é `null`; valores iguais dão `estavel`. O que é "melhorar" depende da métrica
  (por exemplo, menos duplicação é melhor; mais cobertura é melhor).
- Métrica desconhecida → `422` com `"Métrica 'xyz' desconhecida"`.

**Responses**:
- `200 OK` → lista (sem filtro) ou objeto de série (com `?metrica=`)
- `404 Not Found` → `"Repositório não encontrado"`
- `422 Unprocessable Entity` → métrica desconhecida ou `id` malformado
