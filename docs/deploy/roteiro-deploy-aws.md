# Roteiro de deploy público na AWS

> Criado em 19/11/2026. Roteiro de trabalho: os valores de custo são aproximados (confirme na calculadora da
> AWS) e os passos que dependem do console da AWS devem ser conferidos na hora, porque a interface muda.
> Depois do deploy, registre o que foi decidido de fato em um ADR (ADR-016) e atualize o README.

## 1. Arquitetura recomendada (fase 1)

Um único servidor **EC2** rodando o que já existe: o `docker-compose.prod.yml` (backend, worker Celery, Postgres e
Redis) mais um **proxy reverso Caddy** que serve o build estático do frontend e encaminha `/api` ao backend, com HTTPS
automático (Let's Encrypt).

```
Usuário ──HTTPS──▶ Route 53 (A) ──▶ Elastic IP ──▶ EC2 (Ubuntu 24.04, t3.medium, 30 GB gp3)
                                                    └─ Caddy :80/:443
                                                         ├─ /            → frontend estático (npm run build)
                                                         └─ /api/*       → backend :3001 (rede interna do compose)
                                                    └─ backend + celery-worker + postgres + redis (volumes nomeados)
```

**Por que esta escolha**
- O projeto já foi desenhado para isso (ADR-007: backend atrás de um proxy com HTTPS, Postgres e Redis sem portas
  públicas, credenciais obrigatórias). É o caminho de menor risco para entregar no prazo.
- **Mesmo domínio para o site e a API.** O cookie do refresh token é `SameSite=Lax` com `Secure`; site e API em origens
  diferentes dariam problema de cookie e de CORS. Com o Caddy na frente, tudo sai do mesmo domínio.
- Custo previsível: cerca de **US$ 30–40 por mês** (t3.medium, disco, IP, DNS), contra mais de US$ 100 por mês na
  versão "totalmente gerenciada" (ver a seção 8).
- Ensina o essencial da AWS: conta e IAM, VPC e Security Groups, EC2, EBS, Elastic IP, Route 53, SSM, CloudWatch.

**Dimensionamento.** O worker baixa e analisa repositórios de terceiros (até 400 MB extraídos, ADR-009), e até 4
análises síncronas rodam ao mesmo tempo. Com `t3.small` (2 GB) isso fica apertado; use **`t3.medium` (4 GB)** e crie
2 GB de swap. Dá para reduzir depois, olhando o consumo real no CloudWatch.

## 2. Decisões e pré-requisitos (resolver antes de começar)

| # | Item | Observação |
|---|---|---|
| 1 | **Domínio próprio** (T079) | Necessário também para o e-mail (item 2). Registro.br (`.com.br`) ou Route 53 (`.com`, ~US$ 15/ano). |
| 2 | **Resend com domínio verificado** | Sem isso o Resend só entrega e-mails à conta dona da chave (ADR-005): **a recuperação de senha não funcionaria para os usuários**. Verifique o domínio no Resend (registros DNS SPF/DKIM) e defina `RESEND_API_KEY` e `EMAIL_FROM`. |
| 3 | **Conta AWS** | Ative o MFA no usuário raiz e crie um usuário administrador (não use o raiz no dia a dia). Veja se há créditos (conta nova, AWS Academy ou programa da faculdade). |
| 4 | **Região** | `sa-east-1` (São Paulo) tem menos latência e custa mais; `us-east-1` é mais barata. Recomendo **`sa-east-1`** se o público for o Brasil; para o TCC a diferença de custo é pequena. |
| 5 | **Alerta de custo** | Crie um *Budget* (ex.: US$ 40/mês) com e-mail de aviso **antes** de criar qualquer recurso. |
| 6 | **`GITHUB_TOKEN` no servidor** | Sem token, a API do GitHub limita a 60 requisições por hora no IP do servidor, e a cobertura de testes depende dele. Vale até 01/02/2027 (renovar). |

## 3. Passo 1 — preparar o repositório (um PR)

Mudanças de código/infra que o deploy precisa e que ainda não existem:

- [ ] `deploy/Caddyfile` (domínio, `encode gzip`, `handle /api/*` e `handle /health` → `reverse_proxy backend:3001`, o resto com
  `try_files {path} /index.html` para o roteamento do React).
- [ ] Serviço `caddy` no `docker-compose.prod.yml` (portas 80/443, volumes para o certificado e para o `dist/` do
  frontend) e o backend **sem** publicar a porta no host.
- [ ] `FORWARDED_ALLOW_IPS`: com o Caddy na mesma rede do compose, use a sub-rede do compose (e confirme na prática, na
  verificação, que o rate limit enxerga o IP real do usuário e não o do proxy).
- [ ] Build do frontend com `VITE_API_URL` **vazio** (mesma origem; o `api.ts` usa `??`, então a string vazia vale) e
  teste local do build servido pelo Caddy.
- [ ] `scripts/deploy.sh`: `git pull`, `npm ci && npm run build`, `docker compose … up -d --build`, `alembic upgrade head`.
- [ ] README/ADR-007: documentar a topologia nova.

## 4. Passo 2 — conta AWS e segurança básica

- [ ] MFA no usuário raiz; usuário/perfil administrador; Budget configurado (item 5 acima).
- [ ] Região escolhida (item 4), usada em tudo.

## 5. Passo 3 — rede e servidor

- [ ] **Security Group**: entrada só **80 e 443** (0.0.0.0/0). **Sem porta 22**: o acesso administrativo é pelo
  **SSM Session Manager** (perfil IAM `AmazonSSMManagedInstanceCore` na instância). Menos superfície de ataque e é um
  bom aprendizado.
- [ ] **EC2**: Ubuntu 24.04 LTS, `t3.medium`, disco **gp3 de 30 GB** (com *Delete on termination* **desligado** para o
  volume de dados, ou use um volume separado para `/var/lib/docker`).
- [ ] **Elastic IP** associado à instância (o IP não muda se ela for reiniciada).
- [ ] Swap de 2 GB; atualizações automáticas de segurança (`unattended-upgrades`).
- [ ] Docker Engine + plugin do Compose (repositório oficial da Docker).

## 6. Passo 4 — DNS e HTTPS

- [ ] Zona hospedada no **Route 53** (ou apontar o domínio do Registro.br para ela) e registro **A** para o Elastic IP.
- [ ] Subir o Caddy: ele obtém e renova o certificado sozinho (as portas 80/443 precisam estar abertas e o DNS
  propagado).

## 7. Passo 5 — subir a aplicação

- [ ] Clonar o repositório no servidor e criar o `.env` de produção **no servidor** (nunca no Git), com permissão `600`:
  segredos gerados com `python -c "import secrets; print(secrets.token_urlsafe(48))"` para `JWT_SECRET`,
  `JWT_REFRESH_SECRET`, `DB_PASSWORD` e `REDIS_PASSWORD`; `FRONTEND_URL=https://seu-dominio`;
  `CORS_ORIGINS=["https://seu-dominio"]`; `GITHUB_TOKEN`; `RESEND_API_KEY` e `EMAIL_FROM`.
  Guarde uma cópia dos segredos no **SSM Parameter Store** (`SecureString`) ou no seu gerenciador de senhas.
- [ ] `docker compose -f docker-compose.prod.yml up -d --build` e `alembic upgrade head`.
- [ ] A API recusa iniciar com segredo fraco (ADR-007): se não subir, leia a mensagem — ela lista tudo que está errado.

## 8. Passo 6 — verificação pós-deploy

- [ ] `https://seu-dominio/health` responde; o certificado é válido; HTTP redireciona para HTTPS.
- [ ] Cadastro, login e logout; o cookie do refresh token vem `HttpOnly; Secure; SameSite=Lax`.
- [ ] Cadastrar um repositório e executar uma análise (síncrona e uma grande, assíncrona); histórico e tendência.
- [ ] Gerar o PDF do laudo e reiniciar os containers: o PDF continua baixando (volume `reports_data_prod`).
- [ ] **Recuperar senha para um e-mail de outra pessoa**: o e-mail chega (domínio verificado no Resend).
- [ ] **Rate limit pelo IP real**: 11 logins errados em 1 minuto devolvem 429 só para você, e não para todos.
- [ ] Rodar a suíte E2E do Playwright apontando para a URL pública (`E2E_BASE_URL`); os testes criam contas e repositórios de verdade, então use uma conta de teste e apague os dados depois.
- [ ] Postgres e Redis não respondem de fora (varredura de portas a partir de outra máquina: só 80/443 abertas).

## 9. Operação depois do deploy

- **Backup** (o volume dos PDFs e o do Postgres precisam entrar, ADR-007): *snapshots* diários do EBS pelo **Data
  Lifecycle Manager** (retenção de 7 dias) + `pg_dump` diário enviado a um bucket **S3** com ciclo de vida. **Teste uma
  restauração** pelo menos uma vez.
- **Monitoramento**: alarmes do CloudWatch (CPU, disco, falha de status da instância) com aviso por e-mail (SNS);
  conferir `docker compose logs` em caso de erro.
- **Atualizar**: `scripts/deploy.sh` (o Dependabot e o `audit.yml` continuam avisando de vulnerabilidades).
- **Renovações**: `GITHUB_TOKEN` até 01/02/2027; domínio; certificado (automático).
- **Rollback**: manter a tag/commit anterior e refazer `deploy.sh`; as migrations são aditivas, mas confirme antes de
  reverter uma que apague dados.

## 10. Evolução opcional (para o currículo, depois da entrega)

Cada item abaixo muda a arquitetura e o custo; só faça depois que a fase 1 estiver estável e entregue.

| Evolução | O que ensina | Custo / esforço |
|---|---|---|
| **RDS PostgreSQL** no lugar do container | banco gerenciado, backups automáticos | +US$ 15–25/mês; só mudar `DATABASE_URL` |
| **S3 + CloudFront** para o frontend | CDN, ACM, origens múltiplas (CloudFront também encaminha `/api`) | baixo; pede ajuste de cookie/CORS |
| **PDFs no S3** | armazenamento de objetos, IAM por perfil | exige **alterar o código** (hoje os PDFs são arquivos locais) |
| **CI/CD** com GitHub Actions + OIDC | deploy sem chaves de acesso fixas | médio |
| **Terraform** | infraestrutura como código | médio; ótimo para o currículo |
| **ECS Fargate + ALB + ElastiCache** | orquestração gerenciada | alto (US$ 100+/mês) e muito mais configuração |

## 11. Pegadinhas já conhecidas

1. **E-mail só chega ao dono da conta Resend** sem domínio verificado (ADR-005). É o item que mais costuma ser esquecido.
2. **IP real no rate limit**: se o `FORWARDED_ALLOW_IPS` estiver errado, todos os usuários aparecem com o IP do proxy e
   dividem o limite de 10 logins por minuto.
3. **Primeira análise lenta** depois de subir os containers: o worker precisa baixar o repositório; acompanhe o log.
4. **Sem `GITHUB_TOKEN`**, a cobertura de testes cai para os arquivos do próprio repositório, e a API do GitHub
   limita a 60 requisições por hora por IP.
5. **Disco cheio**: imagens antigas do Docker acumulam; rodar `docker image prune` de vez em quando e acompanhar o
   alarme de disco.
