# Contract: Autenticação

**Feature**: 001-softmeter-plataforma-mvp | Requisitos: FR-010, US5

Base path: `/api/v1/auth`

## POST /api/v1/auth/register

Cria uma nova conta de usuário.

**Request body**:
```json
{ "email": "dev@example.com", "password": "string (min 8 caracteres)" }
```

**Responses**:
- `201 Created` → `{ "id": "uuid", "email": "string", "access_token": "string", "refresh_token": "string" }`
- `409 Conflict` → email já cadastrado
- `422 Unprocessable Entity` → email inválido ou senha fora da política mínima

## POST /api/v1/auth/login

Autentica um usuário existente.

**Request body**:
```json
{ "email": "dev@example.com", "password": "string" }
```

**Responses**:
- `200 OK` → `{ "access_token": "string", "refresh_token": "string", "token_type": "bearer" }`
- `401 Unauthorized` → credenciais inválidas

## POST /api/v1/auth/refresh

Troca um refresh token válido por um novo access token.

**Request**: refresh token via cookie HTTPOnly (ver `research.md` item 9).

**Responses**:
- `200 OK` → `{ "access_token": "string" }`
- `401 Unauthorized` → refresh token ausente, expirado ou revogado

## POST /api/v1/auth/logout

Revoga o refresh token atual.

**Responses**:
- `204 No Content`

---

Todas as demais rotas (`/api/v1/repositories`, `/api/v1/analyses`, `/api/v1/reports`) exigem o
header `Authorization: Bearer {access_token}`; ausência ou token inválido/expirado retorna
`401 Unauthorized` (FR-010).
