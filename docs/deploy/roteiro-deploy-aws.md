# Roteiro de deploy público na AWS

> Criado em 19/11/2026. Roteiro de trabalho: os valores de custo são aproximados (confirme na calculadora da
> AWS) e os passos que dependem do console da AWS devem ser conferidos na hora, porque a interface muda.
> Depois do deploy, registre o que foi decidido de fato em um ADR (ADR-016) e atualize o README.

## 1. Arquitetura recomendada (fase 1)

Um único servidor **EC2** rodando o que já existe: o `docker-compose.prod.yml` (backend, worker Celery, Postgres e
Redis) mais um **proxy reverso Caddy** que serve o build estático do frontend e encaminha `/api` ao backend, com HTTPS
automático (Let's Encrypt).

```
Usuário ──HTTPS──▶ DNS (A) ──▶ Elastic IP ──▶ EC2 (Ubuntu 24.04, t3.small, 20 GB gp3, us-east-1)
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
- Custo baixo e previsível: cerca de **US$ 21 por mês** (ver a seção de custos abaixo), contra mais de US$ 100 por mês
  na versão "totalmente gerenciada" (seção 10).
- Ensina o essencial da AWS: conta e IAM, VPC e Security Groups, EC2, EBS, Elastic IP, SSM, CloudWatch.

**Dimensionamento.** O worker baixa e analisa repositórios de terceiros (até 400 MB extraídos, ADR-009), e até 4
análises síncronas rodam ao mesmo tempo. Para economizar, comece com **`t3.small` (2 GB) e 2 GB de swap**, e reduza
`MAX_CONCURRENT_SYNC_ANALYSES` para 2 no `.env` (cada análise usa menos memória ao mesmo tempo). Se o consumo real
(`docker stats`, CloudWatch) mostrar falta de memória, suba para `t3.medium` (~US$ 15 a mais por mês) — a troca leva
minutos. Se quiser economizar mais, a `t4g.small` (ARM, ~US$ 3 a menos) serve, mas exige conferir que todas as
dependências têm versão para ARM; só vale se o teste passar.

## Custos (valores aproximados: confirme na calculadora da AWS)

| Item | Valor/mês | Observação |
|---|---|---|
| EC2 `t3.small` (us-east-1) | ~US$ 15 | modo de crédito **standard** (não "unlimited", que cobra CPU extra) |
| IP público (Elastic IP) | ~US$ 3,6 | a AWS cobra todo IPv4 público desde 2024 |
| Disco gp3 de 20 GB | ~US$ 1,6 | 20 GB bastam (sistema + imagens + dados) |
| Backup (S3 + 1 snapshot semanal) | ~US$ 0,5 | cresce pouco |
| DNS | US$ 0 | DNS do próprio Registro.br; Route 53 custa +US$ 0,5 e é opcional |
| Tráfego de saída | US$ 0 | os primeiros 100 GB/mês são gratuitos |
| **Total** | **~US$ 21** | |

**Para não passar disso**
- **Não criar** NAT Gateway (~US$ 32), Load Balancer (~US$ 18), RDS, ElastiCache nem Fargate.
- **Budget** de US$ 25 com avisos aos 80%, ao previsto e aos 100%, e o *Cost Anomaly Detection* (gratuito).
- CloudWatch só com métricas básicas e até 10 alarmes (gratuitos); **não** ligar o monitoramento detalhado nem enviar
  logs ao CloudWatch (a ingestão de logs é cobrada).
- Snapshots com retenção curta; apagar volumes e snapshots órfãos.
- **Plano de desligamento:** depois da avaliação da banca, apague a instância, o disco, o Elastic IP e o bucket. Parar a
  instância não basta: disco e IP continuam cobrando.
- **Créditos:** contas novas podem receber créditos de boas-vindas e a faculdade pode ter AWS Academy; confira ao criar a
  conta e use primeiro o que for gratuito.

## 2. Decisões e pré-requisitos (resolver antes de começar)

| # | Item | Observação |
|---|---|---|
| 1 | **Domínio próprio** (T079) | Necessário também para o e-mail (item 2). Registro.br (`.com.br`, ~R$ 40/ano, só CPF). |
| 2 | **Resend com domínio verificado** | Sem isso o Resend só entrega e-mails à conta dona da chave (ADR-005): **a recuperação de senha não funcionaria para os usuários**. Verifique o domínio no Resend (registros DNS SPF/DKIM) e defina `RESEND_API_KEY` e `EMAIL_FROM`. |
| 3 | **Conta AWS** | Ative o MFA no usuário raiz e crie um usuário administrador (não use o raiz no dia a dia). Veja se há créditos (conta nova, AWS Academy ou programa da faculdade). |
| 4 | **Região** | **`us-east-1` (Virgínia)**: a mais barata. `sa-east-1` (São Paulo) tem menos latência, mas custa ~30% mais; para uma demonstração de TCC a latência não compensa. |
| 5 | **Alerta de custo** | Crie um *Budget* de US$ 25/mês, com avisos aos 80%, ao previsto e aos 100%, **antes** de criar qualquer recurso. |
| 6 | **`GITHUB_TOKEN` no servidor** | Sem token, a API do GitHub limita a 60 requisições por hora no IP do servidor, e a cobertura de testes depende dele. Vale até 01/02/2027 (renovar). |

## 3. Passo 1 — preparar o repositório (um PR)

**Concluído** (PR de infra, #168): mudanças de código/infra que o deploy precisava.

- [x] `deploy/Caddyfile` (domínio, `encode gzip`, `handle /api/*` e `handle /health` → `reverse_proxy backend:3001`, o resto com
  `try_files {path} /index.html` para o roteamento do React).
- [x] Serviço `web` (Caddy) no `docker-compose.prod.yml` (portas 80/443, volumes para o certificado; o `dist/` vai dentro da
  imagem, estágio `prod` do `src/frontend/Dockerfile`) e o backend **sem** publicar a porta no host.
- [x] `FORWARDED_ALLOW_IPS`: com o Caddy na mesma rede do compose, use a sub-rede do compose (e confirme na prática, na
  verificação, que o rate limit enxerga o IP real do usuário e não o do proxy).
- [x] Build do frontend com `VITE_API_URL` **vazio** (mesma origem; o `api.ts` usa `??`, então a string vazia vale) e
  teste local do build servido pelo Caddy.
- [x] `scripts/deploy.sh`: `git pull`, `docker compose … build` (o frontend é construído na imagem), `alembic upgrade head`, `up -d` e teste de `/health`.
- [x] README/ADR-007: documentar a topologia nova.
- [x] Achado no teste: a imagem de produção não tinha o `packaging` e o worker não subia (corrigido; o CI agora constrói a imagem `prod`).

## 4. Passo 2 — conta AWS e segurança básica

- [ ] MFA no usuário raiz; usuário/perfil administrador; Budget configurado (item 5 acima).
- [ ] Região escolhida (item 4), usada em tudo.

## 5. Passo 3 — rede e servidor

- [ ] **Security Group**: entrada só **80 e 443** (0.0.0.0/0). **Sem porta 22**: o acesso administrativo é pelo
  **SSM Session Manager** (perfil IAM `AmazonSSMManagedInstanceCore` na instância). Menos superfície de ataque e é um
  bom aprendizado.
- [ ] **EC2**: Ubuntu 24.04 LTS, `t3.small` com crédito **standard**, disco **gp3 de 20 GB**.
- [ ] **Elastic IP** associado à instância (o IP não muda se ela for reiniciada).
- [ ] Swap de 2 GB; atualizações automáticas de segurança (`unattended-upgrades`).
- [ ] Docker Engine + plugin do Compose (repositório oficial da Docker).

## 6. Passo 4 — DNS e HTTPS

- [ ] No painel de DNS do **Registro.br** (gratuito), registro **A** do domínio para o Elastic IP (Route 53 é opcional e
  custa ~US$ 0,5/mês).
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

- **Backup** (o volume dos PDFs e o do Postgres precisam entrar, ADR-007): `pg_dump` diário enviado a um bucket **S3**
  (centavos por mês, com ciclo de vida de 14 dias) + **um snapshot semanal** do EBS (retenção de 2), que guarda também
  o volume dos PDFs. **Teste uma restauração** pelo menos uma vez.
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

## 12. Entrega contínua (GitHub Actions + SSM) e primeira partida

O Playbook veda o deploy manual por SSH/FTP. Por isso a aplicação **não é atualizada por acesso ao servidor**: depois que o
CI passa na `main`, o fluxo `.github/workflows/deploy.yml` assume uma função da AWS por **OIDC** (token temporário, sem
chaves fixas no repositório) e manda o servidor rodar `scripts/deploy.sh` pelo **AWS Systems Manager (SSM)**. O
servidor nem precisa ter a porta 22 aberta (e não tem).

### 12.1 Configuração única na AWS

1. **Provedor OIDC.** IAM → *Provedores de identidade* → *Adicionar provedor* → **OpenID Connect**. URL do provedor:
   `https://token.actions.githubusercontent.com`; público: `sts.amazonaws.com`.
2. **Função `softmeter-github-deploy`.** IAM → *Funções* → *Criar função* → **Identidade da Web**: provedor
   `token.actions.githubusercontent.com`, público `sts.amazonaws.com`, organização `DC811cunha`, repositório
   `metrologia-software`, ramo `main`. Não anexe nenhuma política gerenciada.
3. **Política em linha** nessa função (só pode mandar comandos para a instância de produção):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ssm:SendCommand",
      "Resource": [
        "arn:aws:ec2:<REGIAO>:<ID-DA-CONTA>:instance/<ID-DA-INSTANCIA>",
        "arn:aws:ssm:<REGIAO>::document/AWS-RunShellScript"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["ssm:GetCommandInvocation", "ssm:ListCommandInvocations"],
      "Resource": "*"
    }
  ]
}
```

### 12.2 Variáveis do repositório (não são segredos)

GitHub → *Settings* → *Secrets and variables* → *Actions* → aba **Variables**:

| Variável | Valor |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | ARN da função `softmeter-github-deploy` |
| `AWS_REGION` | região do servidor (`us-east-2`) |
| `EC2_INSTANCE_ID` | ID da instância `softmeter-prod` |

### 12.3 Primeira partida do servidor (uma vez)

Pelo console da AWS: *Systems Manager* → *Session Manager* → *Iniciar sessão* → `softmeter-prod` (um terminal no
navegador, sem SSH). Lá:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/DC811cunha/metrologia-software/main/scripts/bootstrap-server.sh)" -- softmeter.com.br
```

O script clona o repositório em `/opt/softmeter`, cria o `.env` (os segredos são gerados no próprio servidor e nunca
aparecem na tela; ele só pergunta, sem mostrar, o `GITHUB_TOKEN` e a `RESEND_API_KEY`) e dá a primeira partida. A partir daí,
cada merge na `main` com o CI verde publica sozinho.
