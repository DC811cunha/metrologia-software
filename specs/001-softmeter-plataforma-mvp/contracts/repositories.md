# Contract: Repositórios

**Feature**: 001-softmeter-plataforma-mvp | Requisitos: FR-001, FR-002, FR-011, FR-014, FR-015, US1

Base path: `/api/v1/repositories` (autenticado; resultados sempre escopados ao usuário do token — FR-011)

## Convenções comuns

*(Atualizado em 17/11/2026 — ADR-008, ADR-009 e ADR-014; reflete o comportamento atual.)*

- **Sem token válido** → `401 {"detail": "Não autenticado"}` com `WWW-Authenticate: Bearer`.
- **Erros de negócio** têm sempre o corpo `{"detail": "<mensagem em português>"}`.
- **Erros de validação** (corpo malformado, `id` que não é UUID) → `422` com `detail` em **lista** no
  formato do FastAPI (`type`, `loc`, `msg`, `input`). Não confundir com os `422` de negócio, em que
  `detail` é texto.
- Repositório de **outro usuário** é indistinguível de inexistente: sempre `404` (FR-011).

## Objetos

**Repositório** (`RepositoryResponse`):
```json
{
  "id": "uuid",
  "url": "https://github.com/{owner}/{repo}",
  "owner_nome": "string",
  "linguagens_detectadas": ["python"],
  "status_acesso": "ativo | inacessivel",
  "criado_em": "timestamp"
}
```

**Item da lista** (`RepositoryListItemResponse`): os campos acima e mais

| Campo | Tipo | Significado |
|-------|------|-------------|
| `ultima_analise_status` | `string \| null` | status da tentativa mais recente (`processando`, `concluida` ou `falhou`); `null` se nunca analisado |
| `ultima_analise_id` | `uuid \| null` | id dessa tentativa |
| `total_analises` | `int` | quantidade de análises (qualquer status) |
| `total_relatorios` | `int` | quantidade de relatórios gerados |

O identificador interno do GitHub (`github_id`) **não é exposto** pela API.

## POST /api/v1/repositories

Cadastra um novo repositório GitHub público.

**Request body**:
```json
{ "url": "https://github.com/{owner}/{repo}" }
```

**Comportamento**: consulta as linguagens do repositório no GitHub (ver `research.md` item 2) e grava a
`url` **como foi informada** e o `owner_nome` (`owner/repo`) extraído dela; o nome canônico e o
identificador numérico (`github_id`) só são sincronizados na primeira análise (ver *Identidade do
repositório* abaixo). Rejeita se a interseção das linguagens com `{python, javascript, typescript}` for
vazia (FR-002) e se já existir um cadastro com a mesma URL para o usuário autenticado (FR-015).

**Responses**:
- `201 Created` → objeto **Repositório** (sem os campos extras da lista)
- `409 Conflict` → `"Repositório já cadastrado"` (FR-015)
- `422 Unprocessable Entity`:
  - URL inválida → `detail` em lista (validação de schema);
  - repositório inexistente ou privado → `"Repositório 'owner/repo' inacessível"`;
  - linguagem fora do escopo → `"Repositório 'owner/repo' não contém Python, JavaScript ou TypeScript"` (FR-002)
- `429 Too Many Requests` → cota da API do GitHub esgotada; `"Limite de requisições do GitHub atingido…"`,
  com `Retry-After` (segundos) quando o GitHub informa o prazo
- `502 Bad Gateway` → `"O GitHub está indisponível no momento. Tente novamente em instantes."`

## GET /api/v1/repositories

Lista os repositórios do usuário autenticado.

**Responses**:
- `200 OK` → lista de **Item da lista** (campos da tabela acima)

## GET /api/v1/repositories/{id}

Detalha um repositório do usuário autenticado.

**Responses**:
- `200 OK` → objeto **Repositório** (os campos de resumo da lista só existem em `GET /repositories`)
- `404 Not Found` → `"Repositório não encontrado"` (não existe ou não pertence ao usuário — FR-011)
- `422 Unprocessable Entity` → `id` que não é UUID

## DELETE /api/v1/repositories/{id}

Remove o cadastro de um repositório e **tudo que depende dele**.

**Comportamento**: a exclusão é em cascata e definitiva — apaga as análises, as medições e os relatórios
do repositório, **inclusive os arquivos PDF no disco**. Depois dela, qualquer consulta ou download desses
relatórios responde `404`. A API **não** pede confirmação: a interface do SoftMeter exibe uma janela de
confirmação quando o repositório tem análises ou relatórios (e exclui direto quando não há nada a perder).

**Responses**:
- `204 No Content`
- `404 Not Found` → `"Repositório não encontrado"` (não existe ou não pertence ao usuário)

## Identidade do repositório (ADR-014)

O cadastro é identificado pelo **id numérico do GitHub**, e não só pelo nome, para acompanhar mudanças
fora do SoftMeter. Ao disparar uma análise (ver `analyses.md`), a API compara o repositório com o
registro:

- **Renomeado ou transferido** (mesmo id, outro `owner/repo`): a `url` e o `owner_nome` são atualizados
  automaticamente e a análise segue.
- **Duplicata**: se o usuário já tiver outro cadastro com a URL atual, o cadastro **não é renomeado** (a
  restrição de unicidade impediria) e a análise segue normalmente; os históricos **não são fundidos**
  automaticamente — isso fica a critério do usuário.
- **Nome reaproveitado por outro repositório** (id diferente): a análise é recusada com `409` e o
  usuário deve remover o cadastro e cadastrar de novo.
- Todo cadastro começa sem `github_id` e o recebe na primeira análise; a troca de dono do nome só é
  detectada a partir daí.
