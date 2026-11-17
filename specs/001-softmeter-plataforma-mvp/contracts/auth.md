# Contract: Autenticação

**Feature**: 001-softmeter-plataforma-mvp | Requisitos: FR-010, FR-016, US5

Base path: `/api/v1/auth`

## Sessão e tokens

*(Atualizado em 17/11/2026 — ADR-006 e ADR-008; reflete o comportamento atual.)*

- **Access token** (JWT, 15 min): enviado em `Authorization: Bearer {access_token}`.
- **Refresh token** (JWT, 7 dias): vai **somente** no cookie `softmeter_refresh_token` (`HttpOnly`,
  `SameSite=Lax`, `Path=/api/v1/auth`, `Max-Age` de 7 dias e `Secure` quando `COOKIE_SECURE=true`) —
  **nunca no corpo** das respostas.
- **Versão de sessão:** os dois tokens carregam a `token_version` do usuário. Ela sobe no **logout** e no
  **reset de senha**; um token de versão antiga é recusado (`401`), então a revogação vale para os dois
  tipos de token e é imediata, sem esperar a expiração.
- **Senha:** de 8 a **72 bytes** em UTF-8 (limite do bcrypt); fora disso, `422`.

## POST /api/v1/auth/register

Cria uma nova conta de usuário.

**Request body**:
```json
{ "email": "dev@example.com", "password": "string (8 a 72 bytes)" }
```

**Responses**:
- `201 Created` → `{ "access_token": "string", "token_type": "bearer" }` + cookie do refresh token
- `409 Conflict` → email já cadastrado
- `422 Unprocessable Entity` → email inválido ou senha fora da política (menos de 8 caracteres ou mais de 72 bytes)
- `429 Too Many Requests` → em produção, limite de 10 cadastros/hora por IP excedido

## POST /api/v1/auth/login

Autentica um usuário existente.

**Request body**:
```json
{ "email": "dev@example.com", "password": "string" }
```

**Responses**:
- `200 OK` → `{ "access_token": "string", "token_type": "bearer" }` + cookie do refresh token
- `401 Unauthorized` → credenciais inválidas (inclusive senha com mais de 72 bytes, e com o mesmo custo
  de tempo para e-mail inexistente, sem revelar quais contas existem)

## POST /api/v1/auth/refresh

Troca um refresh token válido por um novo access token.

**Request**: refresh token via cookie HTTPOnly (ver `research.md` item 9).

**Responses**:
- `200 OK` → `{ "access_token": "string" }`
- `401 Unauthorized` → refresh token ausente, inválido/expirado, usuário inexistente ou **sessão encerrada**
  (versão antiga: depois de logout ou reset de senha)
- `429 Too Many Requests` → em produção, limite de 30 requisições/minuto por IP excedido

## POST /api/v1/auth/logout

Encerra a sessão **no servidor** e apaga o cookie do refresh token.

**Quem está saindo:** identificado pelo **cookie do refresh token** e, se ele faltar ou não for válido,
pelo `Authorization: Bearer {access_token}`. O cookie vem primeiro porque é justamente o que precisa ser
revogado e continua presente quando o access token (15 min) já expirou — o caso mais comum de logout.

**Efeito:** sobe a `token_version` do usuário, o que invalida o refresh token **mesmo que uma cópia dele
tenha vazado** e também o access token. Vale para **todos os dispositivos** (a versão é por usuário, não
por sessão). Só uma sessão **vigente** é revogada: um token de versão antiga (já revogado, ou anterior a um
reset de senha) não identifica ninguém, então não derruba a sessão de um login posterior.

**Idempotente:** responde `204` e apaga o cookie também sem sessão válida (credenciais ausentes, expiradas
ou já revogadas) — não há `401`. Não é vulnerável a CSRF: o cookie é `SameSite=Lax` e não acompanha um
`POST` vindo de outro site.

**Responses**:
- `204 No Content` (sempre; não exige `Authorization`)

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
{ "token": "string", "new_password": "string (8 a 72 bytes)" }
```

**Responses**:
- `204 No Content` → senha atualizada, token marcado como usado e **todas as sessões existentes encerradas**
  (a `token_version` sobe: refresh e access tokens anteriores deixam de valer)
- `400 Bad Request` → `"Token inválido ou expirado"` (mesma mensagem para token inexistente,
  já usado ou vencido)
- `422 Unprocessable Entity` → senha fora da política (menos de 8 caracteres ou mais de 72 bytes)
- `429 Too Many Requests` → limite de 10 requisições/minuto por IP excedido

---

**Rate limiting** (`app/core/rate_limit.py`, ADR-008): `/login`, `/forgot-password` e `/reset-password`
têm, cada um, a sua janela de 10 requisições por minuto por IP; excedê-la retorna `429` com `Retry-After`.
Em **produção** também são limitados, por IP, `/register` (10/hora) e `/refresh` (30/min). O contador pode ser
compartilhado entre réplicas (`RATE_LIMIT_BACKEND=redis`). O `/logout` não é limitado.

Todas as demais rotas — `/api/v1/repositories` e as rotas aninhadas
`/api/v1/repositories/{repository_id}/analyses` e `/api/v1/repositories/{repository_id}/reports` —
exigem o header `Authorization: Bearer {access_token}`; ausência ou token inválido/expirado
retorna `401 Unauthorized` (FR-010).
