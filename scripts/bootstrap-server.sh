#!/usr/bin/env bash
# Preparação ÚNICA do servidor de produção (rode uma vez, como root, por uma sessão do AWS Systems Manager):
#
#   sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/DC811cunha/metrologia-software/main/scripts/bootstrap-server.sh)" -- softmeter.com.br
#
# O que faz: clona o repositório em /opt/softmeter, cria o .env de produção (segredos gerados aqui mesmo, com
# openssl, e que nunca saem do servidor) e dá a primeira partida da aplicação. Depois disso, as atualizações são
# automáticas pelo GitHub Actions (.github/workflows/deploy.yml). Pode ser repetido: não sobrescreve o .env.
#
# Pede, sem mostrar na tela nem gravar no histórico do terminal:
#   - GITHUB_TOKEN  (opcional; cobertura de testes lida do CI e limite maior da API do GitHub)
#   - RESEND_API_KEY (e-mail de recuperação de senha; sem ela o link só aparece no log)
set -euo pipefail

SITE="${1:-}"
REPO_URL="https://github.com/DC811cunha/metrologia-software.git"
DIR="/opt/softmeter"

if [[ -z "$SITE" ]]; then
  echo "Uso: bootstrap-server.sh <dominio>   (ex.: softmeter.com.br)" >&2
  exit 1
fi
if [[ $EUID -ne 0 ]]; then
  echo "Rode como root (sudo)." >&2
  exit 1
fi

for cmd in git docker openssl curl; do
  command -v "$cmd" >/dev/null || { echo "Falta o comando '$cmd'. Instale-o e rode de novo." >&2; exit 1; }
done
docker compose version >/dev/null 2>&1 || { echo "Falta o plugin 'docker compose'." >&2; exit 1; }

echo "==> Código em $DIR"
if [[ -d "$DIR/.git" ]]; then
  git -C "$DIR" pull --ff-only
else
  rm -rf "$DIR"
  git clone "$REPO_URL" "$DIR"
fi
cd "$DIR"

gen() { openssl rand -base64 64 | tr -d '/+=\n' | cut -c1-48; }

if [[ -f .env ]]; then
  echo "==> .env já existe: mantido como está."
else
  echo "==> Criando o .env de produção"
  read -rsp "GITHUB_TOKEN (Enter para pular): " GITHUB_TOKEN_IN; echo
  read -rsp "RESEND_API_KEY (Enter para pular): " RESEND_KEY_IN; echo

  umask 077
  cat > .env <<EOF
# Gerado por scripts/bootstrap-server.sh em $(date -u +%Y-%m-%dT%H:%M:%SZ). NÃO versionar.
SITE_ADDRESS=${SITE}
FRONTEND_URL=https://${SITE}
CORS_ORIGINS=["https://${SITE}"]
FORWARDED_ALLOW_IPS=172.29.0.0/24

DB_USER=softmeter
DB_NAME=softmeter_db
DB_PASSWORD=$(gen)
REDIS_PASSWORD=$(gen)
JWT_SECRET=$(gen)
JWT_REFRESH_SECRET=$(gen)

GITHUB_TOKEN=${GITHUB_TOKEN_IN}
RESEND_API_KEY=${RESEND_KEY_IN}
EMAIL_FROM=SoftMeter <noreply@${SITE}>

# Análises: o servidor é pequeno (2 GB); poucas análises síncronas ao mesmo tempo.
MAX_CONCURRENT_SYNC_ANALYSES=2
EOF
  chmod 600 .env
  echo "    .env criado (permissão 600). Os segredos não foram exibidos."
fi

echo "==> Primeira partida da aplicação (pode levar alguns minutos)"
bash ./scripts/deploy.sh

echo
echo "Pronto. Teste: https://${SITE}/health"
