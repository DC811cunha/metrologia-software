# ADR-006: Revogação de Sessão por Versão de Token e Limite de Senha em Bytes

**Data:** 08/11/2026
**Status:** Aceito
**Autor:** Diego Cunha
**Origem:** revisão por pares do Sandro Machiniski — issues #95 e #96

---

## Contexto

Dois problemas de autenticação foram apontados na revisão:

1. **Senha com mais de 72 bytes derrubava a API com erro 500.** O bcrypt só considera os 72
   primeiros *bytes* da senha e, a partir da versão 5, lança `ValueError` em vez de truncar em
   silêncio. Os schemas só validavam o mínimo (8 caracteres), então cadastro, login e reset
   respondiam 500 — e, no login, só quando o e-mail existia, o que **revelava quais e-mails estão
   cadastrados**. Mesmo com senha curta, o login de e-mail inexistente respondia imediatamente
   enquanto o de e-mail cadastrado pagava o custo do bcrypt (diferença de tempo mensurável).
2. **A sessão não podia ser encerrada no servidor.** O refresh token é um JWT sem estado de
   7 dias: redefinir a senha ou fazer logout só apagava o cookie no navegador, e qualquer cópia do
   token continuava gerando access tokens até expirar. Além disso, o refresh token também ia no
   corpo da resposta (anulando o benefício do cookie `HttpOnly`), e o cookie era emitido sem
   `Secure` e sem validade.

## Decisão

**Senha**
- Os schemas de cadastro e de reset rejeitam senhas com mais de **72 bytes em UTF-8** (422). O
  limite é em bytes, não em caracteres: 37 caracteres acentuados já passam de 72 bytes.
- `verify_password` trata `ValueError` como senha incorreta; o login nunca devolve 500 por isso.
- Quando o e-mail não existe, o login executa uma verificação contra um hash fictício
  (`equalize_login_timing`), igualando o custo de tempo ao do e-mail cadastrado.
- `bcrypt` fixado em `>=4.1,<6` para o ambiente de CI e o de produção se comportarem igual.

**Sessão**
- A tabela `users` ganha `token_version` (inteiro, padrão 0). Todo JWT (access e refresh) carrega
  a versão vigente na emissão (`ver`); tokens com versão diferente da atual são recusados em
  `get_current_user` e em `/refresh`.
- A versão é incrementada no **reset de senha** e no **logout** — o que invalida o refresh token
  mesmo que uma cópia tenha vazado. Tokens emitidos antes desta mudança não têm o campo e são
  tratados como versão 0, então as sessões existentes continuam válidas após o deploy.
- O refresh token deixa de ir no corpo das respostas de cadastro/login; vai somente no cookie.
- O cookie ganha `Max-Age` igual à validade do token (7 dias) e `Secure` configurável por
  `COOKIE_SECURE` (deve ser ligado sempre que a API for servida por HTTPS).

## Justificativa

- **Versão por usuário em vez de lista de tokens revogados:** mantém o refresh token stateless (sem
  tabela de tokens nem consulta extra além do `db.get(User)` que já existia) e dá revogação imediata.
- **Bytes, não caracteres:** é o limite real do algoritmo; validar caracteres deixaria passar
  senhas com acentos ou emoji que continuariam quebrando.
- **Pré-hash (SHA-256 + base64) foi descartado:** permitiria senhas longas, mas mudaria o formato
  de todos os hashes já gravados. Um limite de 72 bytes é suficiente e não exige migração de dados.

## Consequências

- **Logout encerra todas as sessões do usuário**, em todos os dispositivos, porque a versão é por
  usuário e não por dispositivo. É o comportamento mais seguro com o menor estado; revogar apenas o
  dispositivo atual exigiria registrar cada refresh token (tabela de sessões).
- **Não há rotação do refresh token** em `/refresh`. Com revogação por versão, rotacionar sem
  detecção de reuso acrescentaria pouco; fica como melhoria possível junto de uma tabela de sessões.
- **O access token continua em `localStorage`** (escolha já assumida no projeto). A revogação por
  versão limita o estrago de um roubo, mas não o impede; uma CSP restritiva é a defesa
  complementar a considerar no deploy público.
- Exige a migration `add token_version to users` (`alembic upgrade head`) antes de subir esta versão.
- No deploy público com HTTPS, definir `COOKIE_SECURE=true`.
