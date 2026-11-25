# Roteiro de deploy público na AWS

> Criado em 19/11/2026. Roteiro de trabalho: os valores de custo são aproximados (confirme na calculadora da
> AWS) e os passos que dependem do console da AWS devem ser conferidos na hora, porque a interface muda.
> Depois do deploy, registre o que foi decidido de fato em um ADR (ADR-016) e atualize o README.

## 1. Arquitetura recomendada (fase 1)

Um único servidor **EC2** rodando o que já existe: o `docker-compose.prod.yml` (backend, worker Celery, Postgres e
Redis) mais um **proxy reverso Caddy** que serve o build estático do frontend e encaminha `/api` ao backend, com HTTPS
automático (Let's Encrypt).

```
Usuário ──HTTPS──▶ DNS (A) ──▶ Elastic IP ──▶ EC2 (Ubuntu 26.04, t3.small, 30 GiB gp3, us-east-2)
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
| EC2 `t3.small` (us-east-2) | ~US$ 15 | modo de crédito **standard** (não "unlimited", que cobra CPU extra) |
| IP público (Elastic IP) | ~US$ 3,6 | a AWS cobra todo IPv4 público desde 2024 |
| Disco gp3 de 30 GiB | ~US$ 2,4 | sistema, imagens do Docker e dados (o volume criado tem 30 GiB) |
| Backup (snapshot semanal do EBS, retenção 2) | ~US$ 0,5 a 1 | só os blocos usados; sem S3 |
| DNS | US$ 0 | DNS do próprio Registro.br; Route 53 custa +US$ 0,5 e é opcional |
| Tráfego de saída | US$ 0 | os primeiros 100 GB/mês são gratuitos |
| **Total** | **~US$ 22** | |

**Para não passar disso**
- **Não criar** NAT Gateway (~US$ 32), Load Balancer (~US$ 18), RDS, ElastiCache nem Fargate.
- **Budget** de US$ 25 com avisos quando o gasto real passar de 85% e de 100% e quando o previsto passar de 100% (criado como `orcamento-softmeter`; o e-mail do destinatário precisa estar **verificado**, senão os avisos não chegam), e o *Cost Anomaly Detection* (gratuito).
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
| 4 | **Região** | **`us-east-2` (Ohio)**: tem o mesmo preço da `us-east-1` (Virgínia), as mais baratas. `sa-east-1` (São Paulo) tem menos latência, mas custa ~30% mais; para uma demonstração de TCC a latência não compensa. |
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

## Estado do deploy (24/11/2026)

A aplicação está **no ar em https://softmeter.com.br** (EC2 `softmeter-prod`, `t3.small`, `us-east-2`). Confirmado:
DNS apontando para o servidor, certificado Let's Encrypt válido, HTTP redirecionando para HTTPS, `/health` respondendo, só as
portas 80 e 443 abertas (22, 3001, 5432 e 6379 fechadas), deploy automático **disparado à mão** com sucesso pelo GitHub Actions
(seção 12). Testado pelo dono do projeto em produção: login, cadastro de repositório, análise, emissão de relatório e
recuperação de senha. **Pendências:** e-mail de recuperação para uma caixa que não seja a do dono da conta Resend, rate limit pelo IP real,
PDF depois de reiniciar os containers e uma execução assíncrona (repositório grande). O disparo automático do deploy após o CI,
os backups, o alarme e o Budget já foram conferidos (ver abaixo).
Os itens marcados abaixo foram conferidos; os demais continuam abertos.

**Conferido no console em 25/11/2026:** Budget `orcamento-softmeter` (US$ 25/mês) com e-mail verificado; Elastic IP `3.16.242.174` associado à instância; Security Group `launch-wizard-1` só com HTTP (80) e HTTPS (443) de entrada; crédito da instância **standard** (sem cobrança extra por CPU); IMDSv2 obrigatório; AMI **Ubuntu 26.04**; volume **gp3 de 30 GiB** (não criptografado); nenhum bucket S3 e nenhum segredo no Secrets Manager. **Backup criado em 25/11:** política do Data Lifecycle Manager `policy-01d161371a0141256` (snapshot semanal do volume marcado `backup=semanal`, domingo às 03:00 UTC, retenção de 2). **Também em 25/11:** snapshot manual `snap-0a14eee3cfb73cd8d` (12,4 GiB gravados, concluído); **teste de restauração** feito (um volume criado a partir dele ficou *Disponível*, com verificação de status OK, e foi apagado); **alarme** `softmeter-prod-status-check` (falha de verificação de status, 2 períodos de 5 minutos) em estado OK, com aviso por e-mail pelo tópico SNS `softmeter-alertas` (assinatura confirmada). Pelo Session Manager: swap de 2 GB ativo (`/swapfile`), `unattended-upgrades` habilitado e ativo (`20auto-upgrades` com `Unattended-Upgrade "1"`), disco com 26% de uso (7,1 de 28 GB) e os 5 containers de pé (`db` e `redis` *healthy*). A conta está no plano gratuito (valor devido US$ 0,00): **o acesso à AWS termina em 19/05/2027** ou quando os créditos acabarem, o que vier primeiro; a banca precisa ocorrer antes.

## 4. Passo 2 — conta AWS e segurança básica

- [ ] MFA no usuário raiz; usuário/perfil administrador.
- [x] Budget configurado (item 5 acima): `orcamento-softmeter`, e-mail verificado.
- [x] Região escolhida (item 4), usada em tudo: `us-east-2`.

## 5. Passo 3 — rede e servidor

- [x] **Security Group**: entrada só **80 e 443** (0.0.0.0/0). **Sem porta 22**: o acesso administrativo é pelo
  **SSM Session Manager** (perfil IAM `AmazonSSMManagedInstanceCore` na instância). Menos superfície de ataque e é um
  bom aprendizado.
- [x] **EC2**: Ubuntu 26.04 LTS, `t3.small` com crédito **standard**, disco **gp3 de 30 GiB**.
- [x] **Elastic IP** associado à instância (o IP não muda se ela for reiniciada).
- [x] Swap de 2 GB; atualizações automáticas de segurança (`unattended-upgrades`).
- [x] Docker Engine + plugin do Compose (repositório oficial da Docker).

## 6. Passo 4 — DNS e HTTPS

- [x] No painel de DNS do **Registro.br** (gratuito), registro **A** do domínio para o Elastic IP (Route 53 é opcional e
  custa ~US$ 0,5/mês).
- [x] Subir o Caddy: ele obtém e renova o certificado sozinho (as portas 80/443 precisam estar abertas e o DNS
  propagado).

## 7. Passo 5 — subir a aplicação

- [x] Clonar o repositório no servidor e criar o `.env` de produção **no servidor** (nunca no Git), com permissão `600`:
  segredos gerados com `python -c "import secrets; print(secrets.token_urlsafe(48))"` para `JWT_SECRET`,
  `JWT_REFRESH_SECRET`, `DB_PASSWORD` e `REDIS_PASSWORD`; `FRONTEND_URL=https://seu-dominio`;
  `CORS_ORIGINS=["https://seu-dominio"]`; `GITHUB_TOKEN`; `RESEND_API_KEY` e `EMAIL_FROM`.
  Guarde uma cópia dos segredos no **SSM Parameter Store** (`SecureString`) ou no seu gerenciador de senhas.
- [x] `docker compose -f docker-compose.prod.yml up -d --build` e `alembic upgrade head` (hoje feito por `scripts/deploy.sh`).
- [x] A API recusa iniciar com segredo fraco (ADR-007): se não subir, leia a mensagem — ela lista tudo que está errado.

## 8. Passo 6 — verificação pós-deploy

- [x] `https://seu-dominio/health` responde; o certificado é válido; HTTP redireciona para HTTPS.
- [x] Cadastro, login e logout (testado em produção); o cookie do refresh token vem `HttpOnly; Secure; SameSite=Lax`.
- [x] Cadastrar um repositório e executar uma análise (testado em produção; falta testar uma grande, assíncrona); histórico e tendência.
- [ ] Gerar o PDF do laudo e reiniciar os containers: o PDF continua baixando (volume `reports_data_prod`).
- [ ] **Recuperar senha para um e-mail de outra pessoa**: o e-mail chega (domínio verificado no Resend).
- [ ] **Rate limit pelo IP real**: 11 logins errados em 1 minuto devolvem 429 só para você, e não para todos.
- [ ] Rodar a suíte E2E do Playwright apontando para a URL pública (`E2E_BASE_URL`); os testes criam contas e repositórios de verdade, então use uma conta de teste e apague os dados depois.
- [x] Postgres e Redis não respondem de fora (varredura a partir de outra máquina em 24/11: 22, 3001, 5432 e 6379 fechadas ou filtradas; só 80 e 443 abertas).

## 9. Operação depois do deploy

- **Backup** (o volume dos PDFs e o do Postgres precisam entrar, ADR-007): **snapshot semanal do EBS** pelo Data Lifecycle
  Manager (`policy-01d161371a0141256`: volume com a etiqueta `backup=semanal`, domingo às 03:00 UTC, retenção de 2), que
  guarda o Postgres e os PDFs juntos (consistência de falha, suficiente para a demonstração). Não há `pg_dump` para o S3, para
  não criar mais um serviço. Para ter uma cópia fora do calendário, crie um snapshot manual (Volumes → Ações → Criar
  snapshot) e apague-o depois da banca. **Restauração testada em 25/11** (criar um volume a partir do snapshot, ver que ele fica
  *Disponível* e apagá-lo em seguida, sem anexá-lo e sem etiquetas, para a política semanal não o enxergar).
- **Monitoramento**: alarme do CloudWatch `softmeter-prod-status-check` (falha de verificação de status da instância, 2 períodos
  de 5 minutos) com aviso por e-mail pelo tópico SNS `softmeter-alertas` (a assinatura por e-mail precisa estar **confirmada**,
  senão o aviso não chega). Alarmes de CPU e disco não foram criados; conferir `docker compose logs` em caso de erro.
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
| **OIDC** no lugar da chave do deploy (exige os recursos avançados da AWS) | deploy sem chaves de acesso fixas | baixo no código, mas pede upgrade e cartão |
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
CI passa na `main`, o fluxo `.github/workflows/deploy.yml` usa uma credencial da AWS de **privilégio mínimo** para mandar o
servidor rodar `scripts/deploy.sh` pelo **AWS Systems Manager (SSM)**. O servidor não tem a porta 22 aberta.

> **Por que uma chave de acesso e não o OIDC?** O OIDC (token temporário, sem chave fixa) seria o melhor, mas o provedor de
> identidade só existe com os "recursos avançados" da AWS, que exigem o upgrade da conta e um cartão de pagamento. Com a
> conta no plano gratuito e sem cartão (decisão de segurança financeira pessoal), usa-se um usuário IAM que **só** pode
> mandar comandos SSM para a instância: a chave não cria recursos nem gera cobrança. Ver o ADR-016. Se um dia a conta
> tiver os recursos avançados, troque a etapa de credenciais do workflow pelo OIDC (`role-to-assume`).

### 12.1 Usuário IAM de deploy (uma vez, na AWS)

1. **IAM → Usuários → Criar usuário**, nome `softmeter-github-deploy`. **Não** marque o acesso ao console.
2. Em permissões, **não** anexe nenhuma política gerenciada. Depois de criado, abra o usuário → *Adicionar permissões* →
   **Criar política em linha** → aba **JSON**, com este conteúdo (troque `<ID-DA-CONTA>` e `<ID-DA-INSTANCIA>`; a região é
   a do servidor, `us-east-2`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ssm:SendCommand",
      "Resource": [
        "arn:aws:ec2:us-east-2:<ID-DA-CONTA>:instance/<ID-DA-INSTANCIA>",
        "arn:aws:ssm:us-east-2::document/AWS-RunShellScript"
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

3. No usuário → **Credenciais de segurança → Criar chave de acesso**, caso de uso **"Aplicativo em execução fora da AWS"**.
   Copie os dois valores (ID e chave secreta) **direto para o GitHub** (12.2). A chave secreta só aparece uma vez; não a
   cole em chats, e-mails nem arquivos.

### 12.2 GitHub: environment `production`, variáveis e segredos

1. **Settings → Environments → New environment**, nome `production`.
2. Em **Deployment branches and tags**, escolha **Selected branches and tags** e adicione a regra `main` (só a `main`
   consegue usar os segredos).
3. Ainda no environment, em **Environment variables**:

| Variável | Valor |
|---|---|
| `AWS_REGION` | `us-east-2` |
| `EC2_INSTANCE_ID` | ID da instância `softmeter-prod` (começa com `i-`) |

4. Em **Environment secrets**: `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY` (os valores do passo 3 do 12.1).
5. **Actions → Deploy — SoftMeter (AWS) → Run workflow** (ramo `main`) e confira que a execução termina em verde.

**Higiene da chave:** troque-a (crie outra e apague a antiga) se houver qualquer suspeita de vazamento, e **apague o usuário
e a chave** quando a avaliação da banca terminar.

### 12.3 Primeira partida do servidor (uma vez)

Pelo console da AWS: *Systems Manager* → *Session Manager* → *Iniciar sessão* → `softmeter-prod` (um terminal no
navegador, sem SSH). Lá:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/DC811cunha/metrologia-software/main/scripts/bootstrap-server.sh)" -- softmeter.com.br
```

O script clona o repositório em `/opt/softmeter`, cria o `.env` (os segredos são gerados no próprio servidor e nunca
aparecem na tela; ele só pergunta, sem mostrar, o `GITHUB_TOKEN` e a `RESEND_API_KEY`) e dá a primeira partida. A partir daí,
cada merge na `main` com o CI verde publica sozinho.
