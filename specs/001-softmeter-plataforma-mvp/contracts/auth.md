# Contract: Autenticação

**Feature**: 001-softmeter-plataforma-mvp | Requisitos: FR-010, FR-016, US5

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
- `401 Unauthorized` → refresh token ausente, inválido/expirado ou usuário inexistente

## POST /api/v1/auth/logout

Remove o cookie HTTPOnly do refresh token. O JWT em si **não é revogado no servidor** (é
stateless): um refresh token copiado antes do logout continua válido até expirar (7 dias).

**Responses**:
- `204 No Content` (exige `Authorization: Bearer {access_token}`)

## POST /api/v1/auth/forgot-password

*(Adicionado em 16/09/2026 — FR-016, ADR-005.)* Solicita o link de redefinição de senha.

**Request body**:
```json
{ "email": "dev@example.com" }
```

**Comportamento**: se o e-mail estiver cadastrado, cria um token de uso único (guardado só como
hash SHA-256, expira em 60 min) e enfileira o envio do e-mail em uma task Celery; se não estiver,
não faz nada. A resposta é **idêntica e no mesmo tempo** nos dois casos (sem enumeração de contas
nem side-channel de timing).

**Responses**:
- `200 OK` → `{ "message": "Se este e-mail estiver cadastrado, você receberá um link de recuperação em instantes." }`
- `422 Unprocessable Entity` → formato de e-mail inválido
- `429 Too Many Requests` → limite de 10 requisições/minuto por IP excedido

## POST /api/v1/auth/reset-password

*(Adicionado em 16/09/2026 — FR-016, ADR-005.)* Define a nova senha a partir do token recebido por
e-mail (link `{FRONTEND_URL}/reset-password?token=…`).

**Request body**:
```json
{ "token": "string", "new_password": "string (min 8 caracteres)" }
```

**Responses**:
- `204 No Content` → senha atualizada e token marcado como usado
- `400 Bad Request` → `"Token inválido ou expirado"` (mesma mensagem para token inexistente,
  já usado ou vencido)
- `422 Unprocessable Entity` → senha fora da política mínima
- `429 Too Many Requests` → limite de 10 requisições/minuto por IP excedido

---

**Rate limiting**: `/login`, `/forgot-password` e `/reset-password` compartilham a janela de 10
requisições por minuto por IP (`app/main.py`); excedê-la retorna `429`.

Todas as demais rotas — `/api/v1/repositories` e as rotas aninhadas
`/api/v1/repositories/{repository_id}/analyses` e `/api/v1/repositories/{repository_id}/reports` —
exigem o header `Authorization: Bearer {access_token}`; ausência ou token inválido/expirado
retorna `401 Unauthorized` (FR-010).
