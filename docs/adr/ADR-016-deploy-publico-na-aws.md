# ADR-016: Deploy Público na AWS (servidor único, Caddy e entrega contínua por SSM)

**Data:** 24/11/2026
**Status:** Aceito
**Autor:** Diego Cunha
**Origem:** exigência da banca (deploy público e pipeline CI/CD com deploy automatizado) e orientação do professor (AWS)

---

## Contexto

A banca exige a aplicação publicada e um pipeline de CI/CD que publique sozinho (deploy manual por SSH/FTP é motivo de
reprovação). O orçamento é pessoal e apertado (teto de cerca de US$ 25 por mês), e esta foi a primeira publicação de um
projeto. O sistema já tinha um `docker-compose.prod.yml` pensado para ficar atrás de um proxy com HTTPS (ADR-007).

## Decisão

- **Um único servidor EC2** (`softmeter-prod`, Ubuntu 26.04, `t3.small` com crédito *standard*, disco gp3 de 30 GiB, região `us-east-2`) rodando
  o `docker-compose.prod.yml`: Caddy, backend, worker Celery, Postgres e Redis. Custo estimado de ~US$ 22 por mês. Sem NAT
  Gateway, balanceador, RDS, ElastiCache nem Fargate.
- **Caddy** como proxy reverso: serve o build estático do frontend e encaminha `/api` e `/health` ao backend, com HTTPS
  automático (Let's Encrypt). Site e API ficam no **mesmo domínio** (`softmeter.com.br`), porque o cookie do refresh token
  é `SameSite=Lax` + `Secure`. O uvicorn só confia no `X-Forwarded-For` vindo da sub-rede do compose (`172.29.0.0/24`).
- **Sem SSH.** O acesso administrativo é pelo AWS Systems Manager (Session Manager); o Security Group só abre 80 e 443.
- **Entrega contínua:** depois do CI verde na `main`, o workflow `deploy.yml` manda a instância rodar `scripts/deploy.sh`
  (pull, build, migrations, `up -d`, teste de `/health`) por **SSM Run Command**, e falha se o deploy falhar.
- **Credencial do pipeline:** um **usuário IAM de privilégio mínimo** (`softmeter-github-deploy`, sem acesso ao console)
  cuja política só permite `ssm:SendCommand` para a instância de produção e o documento `AWS-RunShellScript` (mais a leitura
  do resultado). A chave de acesso fica em segredos do *environment* `production` do GitHub, restrito à `main`.
- **Backup:** snapshot semanal do volume do EBS pelo Data Lifecycle Manager (etiqueta `backup=semanal`, domingo 03:00 UTC, retenção de 2), que cobre o Postgres e os PDFs; sem `pg_dump` nem S3, para não criar mais serviços.
- **DNS** no próprio Registro.br (gratuito); e-mail de recuperação de senha pelo Resend com o domínio verificado (ADR-005).

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **OIDC** entre o GitHub e a AWS (token temporário, sem chave fixa) | Era a escolha preferida e é o desenho do primeiro `deploy.yml`, mas o provedor de identidade OIDC só existe com os "recursos avançados" da AWS, que exigem o **upgrade da conta e um cartão de pagamento**. Foi descartada por segurança financeira pessoal. |
| Runner próprio do GitHub no servidor | O repositório é público: um PR malicioso poderia executar código no servidor de produção. |
| Servidor consultando o GitHub e se atualizando sozinho | Sem credencial a guardar, mas o deploy deixa de ser feito pelo GitHub Actions, que é o que o Playbook pede para mostrar. |
| RDS, S3 + CloudFront, ECS/Fargate, ALB | Custo (US$ 100+ por mês) e configuração muito acima do necessário para a demonstração; ficam como evolução opcional (roteiro, seção 10). |
| Deploy por SSH | Vetado pelo Playbook e deixaria a porta 22 aberta. |

## Consequências

- **Chave de acesso permanente.** Diferente do OIDC, a chave não expira. O risco é limitado: ela só consegue mandar
  comandos àquela instância (não cria recursos nem gera cobrança), mas um vazamento permitiria rodar comandos no servidor.
  Mitigações: segredo apenas no *environment* `production` (só a `main` o acessa), troca imediata se houver suspeita e
  **exclusão do usuário e da chave quando a avaliação da banca terminar**. Se a conta passar a ter os recursos avançados,
  o OIDC substitui a chave trocando uma única etapa do workflow.
- **Prazo e limites da conta:** a conta está no plano gratuito (créditos e período de teste, sem cartão); o console informa que o acesso à AWS termina quando os créditos acabam ou o período vence (19/05/2027), e o site sai do ar. A banca precisa ocorrer antes. O volume do disco não é criptografado e o backup é por snapshot (consistência de falha); ambos aceitos para a demonstração.
- Um servidor único não tem alta disponibilidade: se a instância cair, o site cai até ela voltar. Aceito para a demonstração.
- O deploy reconstrói as imagens no próprio servidor (alguns minutos de uso de CPU e memória); o `t3.small` com 2 GB de
  swap e `MAX_CONCURRENT_SYNC_ANALYSES` reduzido dá conta.
- Backups, alarmes e o plano de desligamento (apagar instância, disco, IP e bucket depois da banca) estão no roteiro
  (`docs/deploy/roteiro-deploy-aws.md`, seções 9 e 12).
- O teste da stack de produção antes do deploy encontrou um defeito que o CI não via (a imagem `prod` sem o `packaging`,
  que derrubava o worker): o CI agora constrói a imagem de produção e importa os módulos do worker e da API (ADR-007).
