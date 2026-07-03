# Contract: Repositórios

**Feature**: 001-softmeter-plataforma-mvp | Requisitos: FR-001, FR-002, FR-011, FR-014, FR-015, US1

Base path: `/api/v1/repositories` (autenticado; resultados sempre escopados ao usuário do token — FR-011)

## POST /api/v1/repositories

Cadastra um novo repositório GitHub público.

**Request body**:
```json
{ "url": "https://github.com/{owner}/{repo}" }
```

**Comportamento**: consulta o endpoint `languages` do GitHub (ver `research.md` item 2); rejeita
se a interseção com `{python, javascript, typescript}` for vazia (FR-002); rejeita se já existir
um registro com a mesma URL para o usuário autenticado (FR-015).

**Responses**:
- `201 Created` → `{ "id": "uuid", "url": "string", "owner_nome": "string", "linguagens_detectadas": ["python"], "status_acesso": "ativo", "criado_em": "timestamp" }`
- `409 Conflict` → repositório já cadastrado por este usuário (FR-015)
- `422 Unprocessable Entity` → URL inválida, repositório privado/inexistente, ou linguagem fora do escopo (FR-002)

## GET /api/v1/repositories

Lista os repositórios do usuário autenticado.

**Responses**:
- `200 OK` → `[{ "id": "uuid", "url": "string", "owner_nome": "string", "linguagens_detectadas": [...], "status_acesso": "ativo", "ultima_analise_status": "concluida" }]`

## GET /api/v1/repositories/{id}

Detalha um repositório do usuário autenticado.

**Responses**:
- `200 OK` → objeto Repositório completo
- `404 Not Found` → não existe ou não pertence ao usuário (FR-011)

## DELETE /api/v1/repositories/{id}

Remove o cadastro de um repositório e seu histórico associado.

**Responses**:
- `204 No Content`
- `404 Not Found` → não existe ou não pertence ao usuário
