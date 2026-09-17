# ADR-005: Recuperação de Senha via E-mail Transacional (Resend)

**Data:** 16/09/2026
**Status:** Aceito
**Autor:** Diego Cunha

---

## Contexto

O fluxo de autenticação do SoftMeter (registro, login, refresh, logout) não tinha nenhuma forma
de recuperação de acesso: um usuário que esquecesse a senha ficava permanentemente trancado fora
da própria conta, sem alternativa além de registrar um e-mail novo. Isso é inaceitável para
qualquer aplicação com usuários reais, e se torna ainda mais urgente com o próximo passo do
projeto — colocar o SoftMeter no ar publicamente, para qualquer pessoa poder usar.

A implementação de "esqueci minha senha" exige duas decisões que a plataforma ainda não tinha
tomado: (1) como gerar e validar o token de redefinição com segurança, e (2) como efetivamente
entregar esse token ao usuário — o que, para uma aplicação web comum, significa enviar um e-mail.

Um ponto concreto que restringiu a decisão: **o projeto não possui domínio próprio** no momento
desta implementação. A maioria dos provedores de e-mail transacional (Resend, SendGrid, SES, etc.)
exige verificação de domínio (registros DNS) para enviar a partir de um remetente com a marca do
próprio produto e para atingir qualquer caixa de entrada de destino.

## Decisão

**Geração e validação do token:**

- Token aleatório de 32 bytes (`secrets.token_urlsafe(32)`), enviado ao usuário por e-mail.
- O banco guarda apenas o **hash SHA-256** do token (`PasswordResetToken.token_hash`), nunca o
  valor bruto — um vazamento do banco não permite a ninguém redefinir senha de outra pessoa.
  SHA-256 (não bcrypt) é intencional aqui: o token já nasce com alta entropia, então o objetivo é
  comparação rápida e exata, não dificultar força bruta sobre uma senha curta escolhida por humano.
- Token de uso único (`usado_em`) e com expiração configurável
  (`password_reset_token_expires_minutes`, padrão 60 minutos).
- `POST /api/v1/auth/forgot-password` sempre responde com a mesma mensagem genérica,
  independentemente de o e-mail existir ou não — evita enumeração de contas cadastradas.
- Ambos os endpoints novos (`forgot-password` e `reset-password`) entram na mesma janela de rate
  limit por IP já usada em `/login` (10 tentativas/minuto), mitigando tanto brute-force de token
  quanto spam de disparo de e-mail.

**Envio do e-mail — Resend em modo sandbox, com fallback de log:**

- Provedor escolhido: **Resend**, via API HTTP direta (`httpx.post`, sem SDK) — mais simples de
  auditar e de trocar depois do que integrar um SDK completo para uma única chamada.
- Sem domínio próprio verificado, o Resend opera em **modo sandbox**: os e-mails só chegam à
  caixa de entrada que é dona da própria conta Resend (o e-mail de teste/desenvolvimento), com o
  remetente fixo `onboarding@resend.dev`. Isso é suficiente para desenvolver e demonstrar o fluxo
  fim-a-fim agora, mas **não atende usuários externos reais**.
- Para não bloquear o desenvolvimento nem quebrar ambientes sem a chave configurada
  (`RESEND_API_KEY` ausente ou vazia), o `EmailService` cai automaticamente para um modo de
  **log**: em vez de chamar a API, registra o link de redefinição no log do backend com nível
  `WARNING`. O mesmo padrão de fallback gracioso já usado para `GITHUB_TOKEN` (ADR-004).
- Qualquer erro de rede (`httpx.HTTPError`) ou resposta não-2xx do Resend é capturado e logado,
  nunca propagado — uma falha no envio de e-mail não pode derrubar o fluxo de autenticação nem
  vazar detalhes internos ao usuário final.

## Justificativa

- **Resolve o problema real sem exigir infraestrutura que o projeto ainda não tem.** Trocar de
  provedor de e-mail (ou verificar um domínio quando ele existir) é uma mudança de configuração
  (`RESEND_API_KEY`, `EMAIL_FROM`), não de código — o `EmailService` já está isolado atrás de uma
  única função (`send_password_reset_email`).
- **Consistente com o padrão de fallback gracioso já estabelecido no projeto** (ADR-004): recursos
  opcionais que dependem de configuração externa nunca quebram o caminho principal quando ausentes.
- **Hash do token, não da senha, com algoritmo mais barato de propósito.** Usar bcrypt (como para
  senhas) aqui seria custo computacional desperdiçado — o risco que bcrypt mitiga (força bruta
  sobre um valor de baixa entropia escolhido por humano) não existe para um token gerado
  criptograficamente com 256 bits de entropia.
- **Mensagem genérica em `forgot-password` é uma prática padrão de segurança** (OWASP) contra
  enumeração de contas via diferença de resposta entre e-mail existente e inexistente.

## Consequências

- **Limitação conhecida e temporária: e-mails só chegam à própria conta Resend em modo sandbox.**
  Isto significa que a funcionalidade **não está pronta para usuários externos reais** enquanto o
  projeto não tiver um domínio próprio verificado no Resend. Isso foi uma escolha consciente do
  autor do projeto para não bloquear o desenvolvimento da feature à espera de um domínio.
- **Bloqueador explícito para o próximo passo do projeto** (deploy público): antes de abrir a
  aplicação para qualquer usuário, será necessário (a) adquirir um domínio, (b) verificá-lo no
  Resend (registros DNS: SPF/DKIM), e (c) atualizar `EMAIL_FROM` para um remetente daquele domínio.
  Nenhuma mudança de código é esperada nessa transição.
- **Requer configuração adicional em produção**: variáveis `RESEND_API_KEY`, `EMAIL_FROM`,
  `FRONTEND_URL` (usada para montar o link de redefinição) e
  `PASSWORD_RESET_TOKEN_EXPIRES_MINUTES` no ambiente do backend e do worker Celery, seguindo o
  mesmo padrão já usado para `GITHUB_TOKEN`.
- Em ambiente de desenvolvimento/CI, sem `RESEND_API_KEY` configurada, o fluxo continua
  inteiramente testável — o link de redefinição aparece no log do backend em vez de um e-mail real.
